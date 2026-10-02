from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Meter:
    id: str
    opening: Decimal
    closing: Decimal
    multiplier: Decimal


def volume(m: Meter) -> Decimal:
    """Actual volume represented by the meter reading.

    The register displays raw units; the real volume is the reading
    difference multiplied by the meter multiplier.
    """
    if m.closing < m.opening:
        raise ValueError("register reversed reading: " + m.id)
    if m.multiplier <= 0:
        raise ValueError("register multiplier must be positive: " + m.id)
    return (m.closing - m.opening) * m.multiplier


def balance(ins: list[Meter], outs: list[Meter], known_loss: Decimal) -> Decimal:
    """Inputs minus outputs minus known loss, in actual (multiplied) volume.

    A negative result is returned unchanged; callers must flag it for
    investigation rather than silently truncating it to zero.
    """
    total_in = sum((volume(x) for x in ins), Decimal(0))
    total_out = sum((volume(x) for x in outs), Decimal(0))
    return total_in - total_out - known_loss
