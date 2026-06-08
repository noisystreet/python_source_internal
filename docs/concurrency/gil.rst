.. _concurrency-gil:

GIL 设计与实现 — 全局解释器锁
====================================

.. epigraph::

   "One Ring to rule them all, One Ring to find them."

   -- J. R. R. Tolkien, The Lord of the Rings (on the GIL)


GIL（Global Interpreter Lock）是 CPython 中最著名也最有争议的设计。
它保证同一时刻只有一个线程在执行 Python 字节码。

从一道题开始
------------

.. code-block:: python

    import threading

    n = 1000000
    counter = 0

    def increment():
        global counter
        for _ in range(n):
            counter += 1

    t1 = threading.Thread(target=increment)
    t2 = threading.Thread(target=increment)
    t1.start(); t2.start()
    t1.join(); t2.join()
    print(counter)  # 2000000 吗？

有了 GIL，``counter += 1`` 在字节码层面被保护——同一时刻只有一个线程执行它。
但结果可能不是 2000000，因为 ``counter += 1`` 在字节码中是三条指令（``LOAD`` / ``ADD`` / ``STORE`` ），
GIL 在线程切换时并不能保证这三条指令的原子性。

.. mermaid::

    flowchart LR
        subgraph Thread1["线程 1"]
            bc1["字节码执行"] --> check1{"有 GIL?"}
            check1 -->|"有"| exec1["执行"]
        end
        subgraph Thread2["线程 2"]
            bc2["字节码执行"] --> check2{"有 GIL?"}
            check2 -->|"无"| wait["等待 GIL"]
            wait --> check2
        end

第一问：GIL 的数据结构
-----------------------

GIL 的核心是一个条件变量（condition variable）+ 一个互斥锁：

.. code-block:: c

    // Python/ceval_gil.c
    struct _gil_runtime_state {
        unsigned long interval;  // 切换间隔（默认 5ms）
        _Py_atomic_int locked;   // GIL 是否被持有
        unsigned long switch_number;  // 切换次数
    };

GIL 本身不复杂——它就是一个**被条件变量保护的互斥锁** 。

第二问：GIL 的获取和释放
------------------------

**获取 GIL (take_gil)**

.. code-block:: c

    static void take_gil(PyThreadState *tstate) {
        while (gil->locked) {
            // 检查是否有其他线程在等待(竞争)
            int switched = gil->switch_number;
            // 如果没有线程在等待，让出 CPU
            if (switched == gil->switch_number) {
                COND_RESET(gil->cond);
                COND_WAIT(gil->cond, gil->mutex);
            }
        }
        // 成功获取 GIL
        gil->locked = 1;
    }

**释放 GIL (drop_gil)**

.. code-block:: c

    static void drop_gil(PyInterpreterState *interp) {
        // 释放 GIL 锁
        gil->locked = 0;
        // 通知等待的线程
        COND_SIGNAL(gil->cond);
    }

第三问：GIL 切换的时机
-----------------------

CPython 默认每执行 **5ms** 的字节码就尝试切换 GIL。

.. code-block:: c

    // ceval.c 主循环中的 GIL 检测
    if (--gil->check_interval <= 0) {
        // 重置计数器
        gil->check_interval = DEFAULT_INTERVAL;
        // 检查是否有其他线程在等待
        if (_Py_atomic_load(&gil->locked)) {
            // 有线程在等待 → 释放 GIL
            drop_gil(tstate);
            // 让出 CPU
            take_gil(tstate);
        }
    }

这个检查在 ``DISPATCH`` 宏中执行——即每条字节码指令执行完毕后。

第四问：GIL 的优缺点
--------------------

**优点：**

- 简化了引用计数的线程安全（不需要原子操作）
- 简化了 C 扩展开发（大部分 C 扩展不需要考虑线程安全）
- 单线程性能好（没有锁竞争的开销）

**缺点：**

- CPU 密集型任务无法利用多核
- I/O 密集型任务虽然不受限（I/O 时释放 GIL），但切换有开销
- 实时性差

通过示例脚本验证
----------------

运行 :file:`examples/gil_demo.py`：

.. code-block:: text

    --- GIL 切换演示 ---
    计数器预期值: 2000000
    实际值: 1598372 (GIL 无法保证单条字节码的原子性)

    --- GIL 可见性 ---
    GIL 默认切换间隔: 5ms

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - GIL 是什么？
     - 全局解释器锁，确保同一时刻只有一个线程执行字节码
   * - 结构？
     - ``_gil_runtime_state`` （locked + cond + interval）
   * - 切换间隔？
     - 默认 5ms
   * - 什么时候切换？
     - 字节码执行间隙（DISPATCH 宏中检查）
   * - 优点？
     - 简化内存管理，简化 C 扩展
   * - 缺点？
     - CPU 密集型无法利用多核

参考资料
--------

- :ref:`concurrency-free-threading` — 无 GIL 模式的方案对比
- :ref:`concurrency-critical-section` — 自由线程下的临界区保护
- :pep:`703` — 自由线程（无 GIL）
- :file:`Python/ceval_gil.c` — GIL 的 take / drop 实现
- `GIL 切换间隔 <https://docs.python.org/3/library/sys.html#sys.setswitchinterval>`__
- `Python GIL 的历史 <https://realpython.com/python-gil/>`__

