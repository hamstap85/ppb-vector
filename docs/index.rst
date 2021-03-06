PPB's 2D Vector class
=====================

.. py:data:: ppb_vector.vector2.Vector
    :annotation: = typing.TypeVar('Vector', bound='Vector2')

    In the following, :py:data:`Vector` is a type variable (an instance of
    :py:class:`TypeVar <typing.TypeVar>`) that denotes either
    :py:class:`Vector2` or any of its subclasses. Implicitely, it is the type of
    ``self``: a method whose return type is :py:data:`Vector` will return a
    vector of the same type that it was called on.


.. autoclass:: ppb_vector.Vector2
   :members:
   :special-members:
   :exclude-members: __init__, __repr__, __weakref__, scale

    .. autoattribute:: x
        :annotation: : float
       
        The X coordinate of the vector

    .. autoattribute:: y
        :annotation: : float
       
        The Y coordinate of the vector
