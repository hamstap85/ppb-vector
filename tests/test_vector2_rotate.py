import math
from math import sqrt

import hypothesis.strategies as st
import pytest  # type: ignore
from hypothesis import assume, example, given, note

from ppb_vector import Vector2
from utils import angle_isclose, angles, floats, isclose, vectors


data_exact = [
    (Vector2(1, 1), -90, Vector2(1, -1)),
    (Vector2(1, 1), 0, Vector2(1, 1)),
    (Vector2(1, 1), 90, Vector2(-1, 1)),
    (Vector2(1, 1), 180, Vector2(-1, -1)),
]


@pytest.mark.parametrize("input, angle, expected", data_exact,
                         ids=[str(angle) for _, angle, _ in data_exact])
def test_exact_rotations(input, angle, expected):
    assert input.rotate(angle) == expected
    assert input.angle(expected) == angle


# angle (in degrees) -> (sin, cos)
#  values from 0 to 45°
#  lifted from https://en.wikibooks.org/wiki/Trigonometry/Selected_Angles_Reference
remarkable_angles = {
    15: ((sqrt(6) - sqrt(2)) / 4, (sqrt(6) + sqrt(2)) / 4),
    22.5: (sqrt(2 - sqrt(2)) / 2, sqrt(2 + sqrt(2)) / 2),
    30: (0.5, sqrt(3) / 2),
    45: (sqrt(2) / 2, sqrt(2) / 2),
}

#  extend up to 90°
remarkable_angles.update({
    90 - angle: (cos_t, sin_t)
    for angle, (sin_t, cos_t) in remarkable_angles.items()
})

#  extend up to 180°
remarkable_angles.update({
    angle + 90: (cos_t, -sin_t)
    for angle, (sin_t, cos_t) in remarkable_angles.items()
})

#  extend up to 360°
remarkable_angles.update({
    angle + 180: (-sin_t, -cos_t)
    for angle, (sin_t, cos_t) in remarkable_angles.items()
})

#  extend to negative angles
remarkable_angles.update({
    -angle: (-sin_t, cos_t)
    for angle, (sin_t, cos_t) in remarkable_angles.items()
})


@pytest.mark.parametrize("angle, trig", remarkable_angles.items(),
                         ids=[str(x) for x in remarkable_angles])
def test_remarkable_angles(angle, trig):
    _angle = math.radians(angle)
    sin_t, cos_t = trig
    sin_m, cos_m = math.sin(_angle), math.cos(_angle)

    assert math.isclose(sin_t, sin_m)
    assert math.isclose(cos_t, cos_m)


data_close = [
    (Vector2(1, 0), angle, Vector2(cos_t, sin_t))
    for (angle, (sin_t, cos_t)) in remarkable_angles.items()
] + [
    (Vector2(1, 1), angle, Vector2(cos_t - sin_t, cos_t + sin_t))
    for (angle, (sin_t, cos_t)) in remarkable_angles.items()
]

data_close_ids = [
    f"(1,0).rotate({x})" for x in remarkable_angles
] + [
    f"(1,1).rotate({x})" for x in remarkable_angles
]


@pytest.mark.parametrize("input, angle, expected", data_close, ids=data_close_ids)
def test_close_rotations(input, angle, expected):
    assert input.rotate(angle).isclose(expected)
    assert angle_isclose(input.angle(expected), angle)


def test_for_exception():
    with pytest.raises(TypeError):
        Vector2("gibberish", 1).rotate(180)


@given(angle=angles())
def test_trig_stability(angle):
    """cos² + sin² == 1

    We are testing that this equation holds, as otherwise rotations
    would (slightly) change the length of vectors they are applied to.
    """
    r_cos, r_sin = Vector2._trig(angle)

    # Don't use exponents here. Multiplication is generally more stable.
    assert math.isclose(r_cos * r_cos + r_sin * r_sin, 1, rel_tol=1e-18)


@given(angle=angles(), n=st.integers(min_value=0, max_value=1e5))
def test_trig_invariance(angle: float, n: int):
    """Test that cos(θ), sin(θ) ≃ cos(θ + n*360°), sin(θ + n*360°)"""
    r_cos, r_sin = Vector2._trig(angle)
    n_cos, n_sin = Vector2._trig(angle + 360 * n)

    note(f"δcos: {r_cos - n_cos}")
    assert isclose(r_cos, n_cos, rel_to=[n / 1e9])
    note(f"δsin: {r_sin - n_sin}")
    assert isclose(r_sin, n_sin, rel_to=[n / 1e9])


@given(v=vectors(), angle=angles(), n=st.integers(min_value=0, max_value=1e5))
def test_rotation_invariance(v: Vector2, angle: float, n: int):
    """Check that rotating by angle and angle + n×360° have the same result."""
    rot_once = v.rotate(angle)
    rot_many = v.rotate(angle + 360 * n)
    note(f"δ: {(rot_once - rot_many).length}")
    assert rot_once.isclose(rot_many, rel_tol=n / 1e9)


@given(initial=vectors(), angle=angles())
def test_rotation_angle(initial, angle):
    """initial.angle( initial.rotate(angle) ) == angle"""
    assume(initial.length > 1e-5)
    rotated = initial.rotate(angle)
    note(f"Rotated: {rotated}")

    measured_angle = initial.angle(rotated)
    d = measured_angle - angle % 360
    note(f"Angle: {measured_angle} = {angle} + {d if d<180 else d-360}")
    assert angle_isclose(angle, measured_angle)


@given(angle=angles(), loops=st.integers(min_value=0, max_value=500))
def test_rotation_stability(angle, loops):
    """Rotating loops times by angle is equivalent to rotating by loops*angle."""
    initial = Vector2(1, 0)

    fellswoop = initial.rotate(angle * loops)
    note(f"One Fell Swoop: {fellswoop}")

    stepwise = initial
    for _ in range(loops):
        stepwise = stepwise.rotate(angle)
    note(f"Step-wise: {stepwise}")

    assert fellswoop.isclose(stepwise, rel_tol=1e-8)
    assert math.isclose(fellswoop.length, initial.length, rel_tol=1e-15)


@given(initial=vectors(), angles=st.lists(angles()))
def test_rotation_stability2(initial, angles):
    """Rotating by a sequence of angles is equivalent to rotating by the total."""
    total_angle = sum(angles)
    fellswoop = initial.rotate(total_angle)
    note(f"One Fell Swoop: {fellswoop}")

    stepwise = initial
    for angle in angles:
        stepwise = stepwise.rotate(angle)
    note(f"Step-wise: {stepwise}")

    # Increase the tolerance on this comparison,
    # as stepwise rotations induce rounding errors
    assert fellswoop.isclose(stepwise, rel_tol=1e-6)

    assert math.isclose(fellswoop.length, initial.length, rel_tol=1e-15)


@given(x=vectors(), y=vectors(), scalar=floats(), angle=angles())
# In this example:
# * x * l == -y
# * Rotation must not be an multiple of 90deg
# * Must be sufficiently large
@example(x=Vector2(1e10, 1e10), y=Vector2(1e19, 1e19), scalar=-1e9, angle=45)
def test_rotation_linearity(x, y, scalar, angle):
    """(l*x + y).rotate is equivalent to l*x.rotate + y.rotate"""
    inner = (scalar * x + y).rotate(angle)
    outer = scalar * x.rotate(angle) + y.rotate(angle)
    note(f"scalar * x + y: {scalar * x + y}")
    note(f"scalar * x.rotate(): {scalar * x.rotate(angle)}")
    note(f"y.rotate(): {y.rotate(angle)}")
    note(f"Inner: {inner}")
    note(f"Outer: {outer}")
    assert inner.isclose(outer, rel_to=[x, scalar * x, y])
