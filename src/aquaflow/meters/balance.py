from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Meter:
    id: str
    opening: Decimal
    closing: Decimal
    multiplier: Decimal


class BalanceResult(Decimal):
    """Net water balance volume.

    Behaves exactly like the Decimal it wraps, while carrying the
    ``needs_investigation`` flag: a negative balance (more water accounted for
    at outputs and known losses than entered) is physically impossible and must
    be investigated rather than silently clamped to zero.
    """

    def __new__(cls, value, needs_investigation=None):
        obj = super().__new__(cls, value)
        if needs_investigation is None:
            needs_investigation = obj < 0
        object.__setattr__(obj, "_needs_investigation", bool(needs_investigation))
        return obj

    @property
    def needs_investigation(self) -> bool:
        return self._needs_investigation

    def __repr__(self):
        return f"BalanceResult({Decimal.__str__(self)}, needs_investigation={self._needs_investigation})"


def volume(m: Meter) -> Decimal:
    """Actual volume represented by the meter interval.

    The register shows display units; the physical volume is the reading
    difference multiplied by the meter multiplier. Equal opening and closing
    readings are valid and represent zero flow. A closing reading below the
    opening reading (illegal reversal) and a non-positive multiplier are
    rejected before any volume can enter the balance.
    """
    if m.closing < m.opening or m.multiplier <= 0:
        raise ValueError("register")
    return (m.closing - m.opening) * m.multiplier


def balance(ins: list[Meter], outs: list[Meter], known_loss: Decimal) -> BalanceResult:
    """Net balance = scaled inputs - scaled outputs - known loss.

    All arithmetic stays in Decimal so meter multipliers and readings retain
    their full precision. A negative result is returned (never truncated to
    zero) and flagged for investigation.
    """
    total_in = sum((volume(x) for x in ins), Decimal(0))
    total_out = sum((volume(x) for x in outs), Decimal(0))
    net = total_in - total_out - known_loss
    return BalanceResult(net, needs_investigation=net < 0)
