import dataclasses
import functools
import typing
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import atan2, copysign, cos, degrees, hypot, isclose, radians, sin, sqrt

__all__ = ('Vector2',)


# Vector or subclass
Vector = typing.TypeVar('Vector', bound='Vector2')

# Anything convertable to a Vector, including lists, tuples, and dicts
VectorLike = typing.Union[
    'Vector2',  # Or subclasses, unconnected to the Vector typevar above
    typing.Tuple[typing.SupportsFloat, typing.SupportsFloat],
    typing.Sequence[typing.SupportsFloat],  # TODO: Length 2
    typing.Mapping[str, typing.SupportsFloat],  # TODO: Length 2, keys 'x', 'y'
]


@functools.lru_cache()
def _find_lowest_type(left: typing.Type, right: typing.Type) -> typing.Type:
    """
    Guess which is the more specific type.
    """
    # Basically, see what classes are unique in each type's MRO and return who
    # has the most.
    lmro = set(left.__mro__)
    rmro = set(right.__mro__)
    if len(lmro) > len(rmro):
        return left
    elif len(rmro) > len(lmro):
        return right
    else:
        # They're equal, just arbitrarily pick one
        return left


def _find_lowest_vector(left: typing.Type, right: typing.Type) -> typing.Type:
    if left is right:
        return left
    elif not issubclass(left, Vector2):
        return right
    elif not issubclass(right, Vector2):
        return left
    else:
        return _find_lowest_type(left, right)


@dataclass(eq=False, frozen=True, init=False, repr=False)
class Vector2:
    """The immutable, 2D vector class of the PursuedPyBear project.

    :py:class:`Vector2` is an immutable 2D Vector, which can be instantiated as
    expected:

    >>> from ppb_vector import Vector2
    >>> Vector2(3, 4)
    Vector2(3.0, 4.0)

    :py:class:`Vector2` implements many convenience features, as well as
    useful mathematical operations for 2D geometry and linear algebra.

    :py:class:`Vector2` acts as an iterable and a sequence, allowing usage like
    converting, indexing, and unpacking:

    >>> v = Vector2(-3, -5)
    >>> list(v)
    [-3.0, -5.0]
    >>> tuple(v)
    (-3.0, -5.0)

    >>> v[0]
    -3.0

    >>> x, y = Vector2(1, 2)
    >>> x
    1.0

    >>> print( *Vector2(1, 2) )
    1.0 2.0

    It also acts mostly like a mapping, when it does not conflict with being a
    sequence. In particular, the coordinates may be accessed by subscripting:

    >>> v["y"]
    -5.0
    >>> v["x"]
    -3.0
    """
    x: float
    y: float

    # Tell CPython that this isn't an extendable dict
    __slots__ = ('x', 'y', '__weakref__')

    @typing.overload
    def __init__(self, x: typing.SupportsFloat, y: typing.SupportsFloat): pass

    @typing.overload
    def __init__(self, other: VectorLike): pass

    def __init__(self, *args, **kwargs):
        if args and kwargs:
            raise TypeError("Got a mix of positional and keyword arguments")

        if not args and not kwargs or len(args) > 2:
            raise TypeError("Expected 1 vector-like or 2 float-like arguments, "
                            f"got {len(args) + len(kwargs)}")

        if kwargs and frozenset(kwargs) != {'x', 'y'}:
            raise TypeError(f"Expected keyword arguments x and y, got: {kwargs.keys().join(', ')}")

        if kwargs:
            x, y = kwargs['x'], kwargs['y']
        elif len(args) == 1:
            x, y = Vector2.convert(args[0])
        elif len(args) == 2:
            x, y = args

        try:
            # The @dataclass decorator made the class frozen, so we need to
            #  bypass the class' default assignment function :
            #
            #  https://docs.python.org/3/library/dataclasses.html#frozen-instances
            object.__setattr__(self, 'x', float(x))
        except ValueError:
            raise TypeError(f"{type(x).__name__} object not convertable to float")

        try:
            object.__setattr__(self, 'y', float(y))
        except ValueError:
            raise TypeError(f"{type(y).__name__} object not convertable to float")

    #: Return a new :py:class:`Vector2` replacing specified fields with new values.
    update = dataclasses.replace

    @classmethod
    def convert(cls: typing.Type[Vector], value: VectorLike) -> Vector:
        """Constructs a vector from a vector-like.

        A vector-like can be:

        - a length-2 :py:class:`Sequence <collections.abc.Sequence>`, whose
          contents are interpreted as the ``x`` and ``y`` coordinates like ``(4, 2)``

        - a length-2 :py:class:`Mapping <collections.abc.Mapping>`, whose keys
          are ``x`` and ``y`` like ``{'x': 4, 'y': 2}``

        - any instance of :py:class:`Vector2` or any subclass.

        :py:meth:`convert` does not perform a copy when ``value`` already has the
        right type.
        """
        # Use Vector2.convert() instead of type(self).convert() so that
        # _find_lowest_vector() can resolve things well.
        if isinstance(value, cls):
            return value
        elif isinstance(value, Vector2):
            return cls(value.x, value.y)
        elif isinstance(value, Sequence) and len(value) == 2:
            return cls(value[0], value[1])
        elif isinstance(value, Mapping) and 'x' in value and 'y' in value and len(value) == 2:
            return cls(value['x'], value['y'])
        else:
            raise ValueError(f"Cannot use {value} as a vector-like")

    @property
    def length(self) -> float:
        """Compute the length of a vector.

        >>> Vector2(45, 60).length
        75.0
        """
        # Surprisingly, caching this value provides no descernable performance
        # benefit, according to microbenchmarks.
        return hypot(self.x, self.y)

    def asdict(self) -> typing.Mapping[str, float]:
        """Convert a vector to a vector-like dictionary.

        >>> v = Vector2(42, 69)
        >>> v.asdict()
        {'x': 42.0, 'y': 69.0}

        The conversion can be reversed by :py:meth:`convert`:

        >>> assert v == Vector2.convert(v.asdict())
        """
        return {'x': self.x, 'y': self.y}

    def __len__(self: Vector) -> int:
        return 2

    def __add__(self: Vector, other: VectorLike) -> Vector:
        """Add two vectors.

        :param other: A :py:class:`Vector2` or a vector-like.
          For a description of vector-likes, see :py:func:`convert`.

        >>> Vector2(1, 0) + (0, 1)
        Vector2(1.0, 1.0)
        """
        rtype = _find_lowest_vector(type(other), type(self))
        try:
            other = Vector2.convert(other)
        except ValueError:
            return NotImplemented
        return rtype(self.x + other.x, self.y + other.y)

    def __sub__(self: Vector, other: VectorLike) -> Vector:
        """Subtract one vector from another.

        :param other: A :py:class:`Vector2` or a vector-like.
          For a description of vector-likes, see :py:func:`convert`.

        >>> Vector2(3, 3) - (1, 1)
        Vector2(2.0, 2.0)
        """
        rtype = _find_lowest_vector(type(other), type(self))
        try:
            other = Vector2.convert(other)
        except ValueError:
            return NotImplemented
        return rtype(self.x - other.x, self.y - other.y)

    def dot(self: Vector, other: VectorLike) -> float:
        """Dot product of two vectors.

        :param other: A :py:class:`Vector2` or a vector-like.
          For a description of vector-likes, see :py:func:`convert`.
        """
        other = Vector2.convert(other)
        return self.x * other.x + self.y * other.y

    def scale_by(self: Vector, scalar: typing.SupportsFloat) -> Vector:
        """Scalar multiplication.

        >>> Vector2(1, 2).scale_by(3)
        Vector2(3.0, 6.0)

        Can also be expressed with :py:meth:`* <__mul__>`:

        >>> 3 * Vector2(1, 2)
        Vector2(3.0, 6.0)
        """
        scalar = float(scalar)
        return type(self)(scalar * self.x, scalar * self.y)

    @typing.overload
    def __mul__(self: Vector, other: VectorLike) -> float: pass

    @typing.overload
    def __mul__(self: Vector, other: typing.SupportsFloat) -> Vector: pass

    def __mul__(self, other):
        """Performs a dot product or scalar product, based on the parameter type.

        :param other: If ``other`` is a scalar (an instance of
          :py:class:`typing.SupportsFloat`), return
          :py:meth:`self.scale_by(other) <scale_by>`.

           >>> 3 * Vector2(1, 1)
           Vector2(3.0, 3.0)

           >>> Vector2(1, 1) * 3
           Vector2(3.0, 3.0)

           >>> Vector2(1, 1).scale_by(3)
           Vector2(3.0, 3.0)

          It is also possible to divide a :py:class:`Vector2` by a scalar:

           >>> Vector2(3, 3) / 3
           Vector2(1.0, 1.0)


        :param other: If ``other`` is a vector-like, return
          :py:meth:`self.dot(other) <dot>`.

          >>> Vector2(1, 1) * (-1, -1)
          -2.0

          Vector-likes are defined in :py:meth:`convert`.
        """
        if isinstance(other, (float, int)):
            return self.scale_by(other)

        try:
            return self.dot(other)
        except (TypeError, ValueError):
            return NotImplemented

    @typing.overload
    def __rmul__(self: Vector, other: VectorLike) -> float: pass

    @typing.overload
    def __rmul__(self: Vector, other: typing.SupportsFloat) -> Vector: pass

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self: Vector, other: typing.SupportsFloat) -> Vector:
        """Perform a division between a vector and a scalar.

        >>> Vector2(3, 3) / 3
        Vector2(1.0, 1.0)
        """
        other = float(other)
        return type(self)(self.x / other, self.y / other)

    def __getitem__(self: Vector, item: typing.Union[str, int]) -> float:
        if hasattr(item, '__index__'):
            item = item.__index__()  # type: ignore
        if isinstance(item, str):
            if item == 'x':
                return self.x
            elif item == 'y':
                return self.y
            else:
                raise KeyError
        elif isinstance(item, int):
            if item == 0:
                return self.x
            elif item == 1:
                return self.y
            else:
                raise IndexError
        else:
            raise TypeError

    def __repr__(self: Vector) -> str:
        return f"{type(self).__name__}({self.x}, {self.y})"

    def __eq__(self: Vector, other: typing.Any) -> bool:
        """Test wheter two vectors are equal.

        :param other: A :py:class:`Vector2` or a vector-like.
          For a description of vector-likes, see :py:func:`convert`.

        >>> Vector2(1, 0) == (0, 1)
        False
        """
        try:
            other = Vector2.convert(other)
        except (TypeError, ValueError):
            return NotImplemented
        else:
            return self.x == other.x and self.y == other.y

    def __iter__(self: Vector) -> typing.Iterator[float]:
        yield self.x
        yield self.y

    def __neg__(self: Vector) -> Vector:
        """Negate a vector.

        Negating a :py:class:`Vector2` produces one with identical length and opposite
        direction. It is equivalent to multiplying it by -1.

        >>> -Vector2(1, 1)
        Vector2(-1.0, -1.0)
        """
        return self.scale_by(-1)

    def angle(self: Vector, other: VectorLike) -> float:
        """Compute the angle between two vectors, expressed in degrees.

        :param other: A :py:class:`Vector2` or a vector-like.
          For a description of vector-likes, see :py:func:`convert`.

        >>> Vector2(1, 0).angle( (0, 1) )
        90.0

        As with :py:meth:`rotate`, angles are signed, and refer to a direct
        coordinate system (i.e. positive rotations are counter-clockwise).

        :py:meth:`angle` is guaranteed to produce an angle between -180° and 180°.
        """
        other = Vector2.convert(other)

        rv = degrees(atan2(other.x, -other.y) - atan2(self.x, -self.y))
        # This normalizes the value to (-180, +180], which is the opposite of
        # what Python usually does but is normal for angles
        if rv <= -180:
            rv += 360
        elif rv > 180:
            rv -= 360

        return rv

    def isclose(self: Vector, other: VectorLike, *,
                abs_tol: typing.SupportsFloat = 1e-09, rel_tol: typing.SupportsFloat = 1e-09,
                rel_to: typing.Sequence[VectorLike] = ()) -> bool:
        """Perform an approximate comparison of two vectors.

        :param other: A :py:class:`Vector2` or a vector-like.
          For a description of vector-likes, see :py:func:`convert`.

        >>> assert Vector2(1, 0).isclose((1, 1e-10))

        :py:meth:`isclose` takes optional, keyword arguments, akin to those of
        :py:func:`math.isclose`:

        :param abs_tol: the absolute tolerance is the minimum magnitude (of the
            difference vector) under which two inputs are considered close,
            without consideration for (the magnitude of) the input values.

        :param rel_tol: the relative tolerance: if the length of the difference
            vector is less than ``rel_tol * input.length`` for any ``input``, the
            two vectors are considered close.

        :param rel_to: an iterable of additional vector-likes which are
            considered to be inputs, for the purpose of the relative tolerance.
        """
        abs_tol, rel_tol = float(abs_tol), float(rel_tol)
        if abs_tol < 0 or rel_tol < 0:
            raise ValueError("Vector2.isclose takes non-negative tolerances")

        other = Vector2.convert(other)

        rel_length = max(
            self.length,
            other.length,
            *map(lambda v: Vector2.convert(v).length, rel_to),
        )

        diff = (self - other).length
        return (diff <= rel_tol * rel_length or diff <= float(abs_tol))

    @staticmethod
    def _trig(angle: typing.SupportsFloat) -> typing.Tuple[float, float]:
        r = radians(angle)
        r_cos, r_sin = cos(r), sin(r)

        if abs(r_cos) > abs(r_sin):
            # From the equation sin(r)² + cos(r)² = 1, we get
            #  sin(r) = ±√(1 - cos(r)²), so we can fix r_sin to that value
            #  preserving its original sign.
            # This way, r_sin² + r_cos² is closer to 1, meaning that the length
            #  of rotated vectors is better preserved
            r_sin = copysign(sqrt(1 - r_cos * r_cos), r_sin)
        else:
            # Same for r_cos
            r_cos = copysign(sqrt(1 - r_sin * r_sin), r_cos)

        return r_cos, r_sin

    def rotate(self: Vector, angle: typing.SupportsFloat) -> Vector:
        """Rotate a vector.

        Rotate a vector in relation to the origin and return a new :py:class:`Vector2`.

        >>> Vector2(1, 0).rotate(90)
        Vector2(0.0, 1.0)

        Positive rotation is counter/anti-clockwise.
        """
        r_cos, r_sin = Vector2._trig(angle)

        x = self.x * r_cos - self.y * r_sin
        y = self.x * r_sin + self.y * r_cos
        return type(self)(x, y)

    def normalize(self: Vector) -> Vector:
        """Return a vector with the same direction and unit length.

        >>> Vector2(3, 4).normalize()
        Vector2(0.6, 0.8)

        Note that :py:meth:`normalize()` is equivalent to :py:meth:`scale(1) <scale>`:

        >>> assert Vector2(7, 24).normalize() == Vector2(7, 24).scale_to(1)
        """
        return self.scale(1)

    def truncate(self: Vector, max_length: typing.SupportsFloat) -> Vector:
        """Scale a given :py:class:`Vector2` down to a given length, if it is larger.

        >>> Vector2(7, 24).truncate(3)
        Vector2(0.84, 2.88)

        It produces a vector with the same direction, but possibly a different
        length.

        Note that :py:meth:`vector.scale(max_length) <scale>` is equivalent to
        :py:meth:`vector.truncate(max_length) <truncate>` when
        :py:meth:`max_length ≨ vector.length <length>`.

        >>> Vector2(3, 4).scale(4)
        Vector2(2.4, 3.2)
        >>> Vector2(3, 4).truncate(4)
        Vector2(2.4, 3.2)

        >>> Vector2(3, 4).scale(6)
        Vector2(3.6, 4.8)
        >>> Vector2(3, 4).truncate(6)
        Vector2(3.0, 4.0)

        Note: :py:meth:`x.truncate(max_length) <truncate>` may sometimes be
        slightly-larger than ``max_length``, due to floating-point rounding
        effects.
        """
        max_length = float(max_length)
        if self.length <= max_length:
            return self

        return self.scale_to(max_length)

    def scale_to(self: Vector, length: typing.SupportsFloat) -> Vector:
        """Scale a given :py:class:`Vector2` to a certain length.

        >>> Vector2(7, 24).scale_to(2)
        Vector2(0.56, 1.92)
        """
        length = float(length)
        if length < 0:
            raise ValueError("Vector2.scale_to takes non-negative lengths.")

        if length == 0:
            return type(self)(0, 0)

        return (length * self) / self.length

    scale = scale_to

    def reflect(self: Vector, surface_normal: VectorLike) -> Vector:
        """Reflect a vector against a surface.

        :param other: A :py:class:`Vector2` or a vector-like.
          For a description of vector-likes, see :py:func:`convert`.

        Compute the reflection of a :py:class:`Vector2` on a surface going
        through the origin, described by its normal vector.

        >>> Vector2(5, 3).reflect( (-1, 0) )
        Vector2(-5.0, 3.0)

        >>> Vector2(5, 3).reflect( Vector2(-1, -2).normalize() )
        Vector2(0.5999999999999996, -5.800000000000001)
        """
        surface_normal = Vector2.convert(surface_normal)
        if not isclose(surface_normal.length, 1):
            raise ValueError("Reflection requires a normalized vector.")

        return self - (2 * (self * surface_normal) * surface_normal)


Sequence.register(Vector2)
