自由线程 (Free-Threading) — 无 GIL 的 CPython
=====================================================

CPython 3.14 引入了实验性的自由线程构建（``--disable-gil``）。

从一道题开始
------------

.. code-block:: shell

    # 编译无 GIL 的 CPython
    ./configure --disable-gil
    make

没有了 GIL，多个线程可以同时执行 Python 字节码——但这也意味引用计数
操作必须线程安全，否则会发生数据竞争。

第一问：平衡引用计数 (BRC)
---------------------------

无 GIL 下最大的挑战是**引用计数**。CPython 引入了**平衡引用计数 (BRC)**：

.. code-block:: c

    // 核心思想：每个对象的主线程本地计数走快速路径
    if (tstate == ob->ob_owner) {
        // 主线程：快速路径，普通 INCREF
        ob->ob_refcnt_local++;
    } else {
        // 跨线程：慢速路径，原子操作
        _Py_atomic_add(&ob->ob_refcnt_shared, 1);
    }

每个 ``PyObject`` 新增了两个字段：

.. code-block:: c

    typedef struct _object {
        Py_ssize_t ob_refcnt;         // 总引用计数
        struct _object *_ob_owner;    // 主线程 ID
        Py_ssize_t ob_refcnt_local;   // 主线程本地计数
        Py_ssize_t ob_refcnt_shared;  // 跨线程共享计数
        PyTypeObject *ob_type;
    } PyObject;

释放时，如果 ``ob_refcnt_local + ob_refcnt_shared == 0``，对象才被真正释放。

第二问：自由线程的影响
-----------------------

**对扩展开发者的影响**

C 扩展需要修改：

- 使用 ``Py_INCREF`` / ``Py_DECREF``（自动适配 BRC）
- 使用 ``Py_BEGIN_CRITICAL_SECTION`` / ``Py_END_CRITICAL_SECTION`` 保护共享状态
- 避免全局可变变量

**对 Python 用户的影响**

- 多线程程序可直接利用多核
- 单线程程序有约 5-10% 的性能损失（BRC 开销）
- ``threading`` 模块不变

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 怎么编译无 GIL 版本？
     - ``./configure --disable-gil``
   * - 引用计数怎么保证安全？
     - BRC（平衡引用计数）：本地 + 共享计数
   * - 对单线程性能的影响？
     - 约 5-10% 性能损失
   * - 对 C 扩展的影响？
     - 需要使用临界区宏保护共享状态

通过示例脚本验证
----------------

无 GIL 构建需要在编译时启用，当前环境为有 GIL 构建。相关概念可通过 :file:`examples/gil_demo.py` 观察 GIL 的行为。

参考资料
--------

- :pep:`703` — 自由线程 CPython
- :file:`Python/ceval_gil.c` — ``--disable-gil`` 构建的 GIL 省略
- :file:`Include/internal/pycore_atomic.h` — 原子操作 API
- :file:`Objects/object.c` — BRC 平衡引用计数实现

