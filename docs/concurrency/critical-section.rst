.. _concurrency-critical-section:

临界区与锁 — 线程安全的基础
====================================

.. epigraph::

   "When two men ride a horse, one must ride behind."

   -- Proverb (on mutual exclusion)


CPython 提供了一套 C 级别的临界区宏，用于保护共享数据的访问。
这部分机制在自由线程（ ``--disable-gil`` ）构建中至关重要。

从一道题开始
------------

.. code-block:: c

    // 保护一个对象的访问
    PyObject *obj = PyList_New(0);
    Py_BEGIN_CRITICAL_SECTION(obj);
    // 临界区内：当前线程独占 obj 的访问权
    PyList_Append(obj, some_value);
    Py_END_CRITICAL_SECTION(obj);

临界区宏包装了锁的获取和释放：进入时加锁，退出时解锁。

.. mermaid::

    flowchart TD
        enter["Py_BEGIN_CRITICAL_SECTION(obj)"] --> check{"GIL 可用?"}
        check -->|"有 GIL"| nop["退化为空操作<br/>GIL 已保证线程安全"]
        check -->|"无 GIL"| trylock["尝试获取 obj->ob_mutex"]
        trylock -->|"成功"| enter_cs["进入临界区"]
        trylock -->|"失败"| wait["等待锁释放"]
        wait --> trylock
        enter_cs --> body["执行临界区代码"]
        body --> exit["Py_END_CRITICAL_SECTION<br/>释放 ob_mutex"]

第一问：临界区宏的展开
----------------------

临界区宏在预处理阶段展开为以下逻辑：

.. code-block:: c

    // Py_BEGIN_CRITICAL_SECTION 的简化展开
    {
        PyThreadState *_py_tstate = _PyThreadState_GET();
        PyObject *_py_op = (op);
        if (_py_tstate != NULL) {
            _PyCriticalSection _py_cs;
            _PyCriticalSection_Begin(&_py_cs, _py_tstate, _py_op);

            // ... 用户代码 ...

            _PyCriticalSection_End(&_py_cs);
        }
    }

``_PyCriticalSection_Begin`` 的内部实现在无 GIL 构建中：

.. code-block:: c

    void _PyCriticalSection_Begin(_PyCriticalSection *cs,
                                   PyThreadState *tstate,
                                   PyObject *op)
    {
    #ifdef Py_GIL_DISABLED
        // 获取对象的互斥锁
        PyMutex_Lock(&op->ob_mutex);
        cs->cs_prev_mutex = tstate->cs_mutex;
        tstate->cs_mutex = &op->ob_mutex;
    #else
        // GIL 构建：什么也不做
    #endif
    }

第二问：锁的类型
----------------

CPython 3.14 内部使用多种锁机制：

**PyMutex** （轻量级互斥锁）
  临界区默认使用的锁。数据结构只有 1 个字（8 字节），无竞争时无系统调用：

  .. code-block:: c

      typedef struct {
          uintptr_t _bits;  // 0 = 未锁定, 1 = 已锁定
      } PyMutex;

      void PyMutex_Lock(PyMutex *m) {
          if (PyMutex_LockFast(m)) return;  // 快速路径：无竞争
          PyMutex_LockSlow(m);              // 慢速路径：进入等待
      }

**PyThread_type_lock**
  平台线程锁（pthreads 或 Windows 临界区）。比 PyMutex 重，用于长时间等待的场景。

**原子操作**
  用于引用计数等简单场景：

  .. code-block:: c

      _Py_atomic_add(&ob->ob_refcnt_shared, 1);
      _Py_atomic_load(&gil->locked);

第三问：临界区的使用场景
------------------------

在 C 扩展中，以下场景需要使用临界区保护：

.. list-table::
   :header-rows: 1

   * - 场景
     - 示例
     - 为什么需要
   * - 修改容器对象
     - ``PyList_SetItem`` 、 ``PyDict_SetItem``
     - 容器内部结构可能被其他线程破坏
   * - 修改对象属性
     - ``PyObject_SetAttr``
     - 属性字典可能被并发修改
   * - 读取后写入的复合操作
     - ``if (PyDict_Contains(d, k)) { PyDict_SetItem(d, k, v); }``
     - 两次操作之间其他线程可能修改了 dict
   * - 修改全局状态
     - 修改模块级别的缓存
     - 多个线程可能同时访问

通过示例脚本验证
----------------

临界区宏在 Python 层面不可见。无 GIL 构建下，C 扩展通过
``Py_BEGIN_CRITICAL_SECTION`` / ``Py_END_CRITICAL_SECTION`` 保护共享状态。

运行 :file:`examples/gil_demo.py` 可以观察 GIL 在多线程下的切换行为。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 临界区宏解决了什么问题？
     - 无 GIL 构建下保护共享对象访问
   * - 有 GIL 时临界区做什么？
     - 退化为空操作（GIL 已保证安全）
   * - PyMutex 是什么？
     - 1 字的轻量级互斥锁，无竞争时无系统调用
   * - 什么时候用 PyThread_type_lock？
     - 长时间等待的场景（I/O、条件变量）

参考资料
--------

- :ref:`concurrency-free-threading` — 临界区在自由线程中的应用
- :ref:`concurrency-gil` — 有 GIL 时无需临界区的对比
- :file:`Python/ceval.c` — 临界区宏
- :pep:`703` — 自由线程
