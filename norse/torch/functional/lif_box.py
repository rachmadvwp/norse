"""
A simplified version of the popular leaky integrate-and-fire neuron model that combines a :mod:`norse.torch.functional.leaky_integrator` with spike thresholds to produce events (spikes).
Compared to the :mod:`norse.torch.functional.lif` modules, this model leaves out the current term, making it computationally simpler but impossible to implement in physical systems because currents cannot "jump" in nature.
It is these sudden current jumps that gives the model its name, because the shift in current is instantaneous and can be drawn as "current boxes".
"""
from typing import NamedTuple, Tuple
import torch
import torch.jit

from norse.torch.functional.threshold import threshold


class LIFBoxParameters(NamedTuple):
    """Parametrization of a boxed LIF neuron

    Parameters:
        tau_mem_inv (torch.Tensor): inverse membrane time
                                    constant (:math:`1/\\tau_\\text{mem}`) in 1/ms
        v_leak (torch.Tensor): leak potential in mV
        v_th (torch.Tensor): threshold potential in mV
        v_reset (torch.Tensor): reset potential in mV
        method (str): method to determine the spike threshold
                      (relevant for surrogate gradients)
        alpha (float): hyper parameter to use in surrogate gradient computation
    """

    tau_mem_inv: torch.Tensor = torch.as_tensor(1.0 / 1e-2)
    v_leak: torch.Tensor = torch.as_tensor(0.0)
    v_th: torch.Tensor = torch.as_tensor(1.0)
    v_reset: torch.Tensor = torch.as_tensor(0.0)
    method: str = "super"
    alpha: float = torch.as_tensor(100.0)


class LIFBoxState(NamedTuple):
    """State of a LIF neuron

    Parameters:
        z (torch.Tensor): recurrent spikes
        v (torch.Tensor): membrane potential
    """

    z: torch.Tensor
    v: torch.Tensor


class LIFBoxFeedForwardState(NamedTuple):
    """State of a feed forward LIF neuron

    Parameters:
        v (torch.Tensor): membrane potential
    """

    v: torch.Tensor


def lif_box_feed_forward_step(
    input_tensor: torch.Tensor,
    state: LIFBoxFeedForwardState,
    p: LIFBoxParameters = LIFBoxParameters(),
    dt: float = 0.001,
) -> Tuple[torch.Tensor, LIFBoxFeedForwardState]:  # pragma: no cover
    r"""Computes a single euler-integration step for a lif neuron-model without
    current terms.
    It takes as input the input current as generated by an arbitrary torch
    module or function. More specifically it implements one integration
    step of the following ODE

    .. math::
        \dot{v} = 1/\tau_{\text{mem}} (v_{\text{leak}} - v + i)

    together with the jump condition

    .. math::
        z = \Theta(v - v_{\text{th}})

    and transition equations

    .. math::
        v = (1-z) v + z v_{\text{reset}}

    Parameters:
        input_tensor (torch.Tensor): the input spikes at the current time step
        state (LIFBoxFeedForwardState): current state of the LIF neuron
        p (LIFBoxParameters): parameters of a leaky integrate and fire neuron
        dt (float): Integration timestep to use
    """
    # compute voltage updates
    dv = dt * p.tau_mem_inv * (input_tensor + p.v_leak - state.v)
    v_decayed = state.v + dv

    # compute new spikes
    z_new = threshold(v_decayed - p.v_th, p.method, p.alpha)
    # compute reset
    v_new = (1 - z_new) * v_decayed + z_new * p.v_reset

    return z_new, LIFBoxFeedForwardState(v=v_new)
