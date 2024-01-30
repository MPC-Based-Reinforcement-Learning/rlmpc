import gymnasium as gym
import numpy as np
from typing import Optional, Union


def erk4_step(f, x, u, p, h):
    k1 = f(x, u, p)
    k2 = f(x + h * k1 / 2, u, p)
    k3 = f(x + h * k2 / 2, u, p)
    k4 = f(x + h * k3, u, p)
    return x + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6


def compute_f_expl(x: np.ndarray, u: np.ndarray, p: dict[float]) -> np.ndarray:
    """
    Explicit dynamics of the evaporation process.
    """
    # Unpack state and input

    algebraic_variables = compute_algebraic_variables(x, u, p)

    X_2 = x[0]

    X_2_dot = (p["F_1"] * p["X_1"] - algebraic_variables["F_2"] * X_2) / p["M"]
    P_2_dot = (algebraic_variables["F_4"] - algebraic_variables["F_5"]) / p["C"]

    return np.array([X_2_dot, P_2_dot])


def compute_algebraic_variables(x: np.ndarray, u: np.ndarray, p: dict[float]) -> dict[float]:
    # Unpack state and input
    X_2, P_2 = x[0], x[1]
    P_100, F_200 = u[0], u[1]

    # Unpack parameters

    # Algebraic equations
    T_2 = p["a"] * P_2 + p["b"] * X_2 + p["c"]
    T_3 = p["d"] * P_2 + p["e"]

    T_100 = p["f"] * P_100 + p["g"]
    U_A1 = p["h"] * (p["F_1"] + p["F_3"])

    Q_100 = U_A1 * (T_100 - T_2)
    F_100 = Q_100 / p["lam_s"]

    F_4 = (Q_100 - p["F_1"] * p["C_p"] * (T_2 - p["T_1"])) / p["lam"]
    Q_200 = p["U_A2"] * (T_3 - p["T_200"]) / (1 + (p["U_A2"] / (2 * p["C_p"] * F_200)))

    # Terms entering the dynamics
    F_5 = Q_200 / p["lam"]

    # Terms entering the cost
    F_2 = p["F_1"] - F_4

    # Algebraic equations
    T_2 = p["a"] * P_2 + p["b"] * X_2 + p["c"]
    T_3 = p["d"] * P_2 + p["e"]

    T_100 = p["f"] * P_100 + p["g"]
    U_A1 = p["h"] * (p["F_1"] + p["F_3"])

    Q_100 = U_A1 * (T_100 - T_2)
    F_100 = Q_100 / p["lam_s"]

    F_4 = (Q_100 - p["F_1"] * p["C_p"] * (T_2 - p["T_1"])) / p["lam"]
    Q_200 = p["U_A2"] * (T_3 - p["T_200"]) / (1 + (p["U_A2"] / (2 * p["C_p"] * F_200)))

    # Terms entering the dynamics
    F_5 = Q_200 / p["lam"]

    # Terms entering the cost
    F_2 = p["F_1"] - F_4

    variables = {
        "T_2": T_2,
        "T_3": T_3,
        "U_A1": U_A1,
        "T_100": T_100,
        "Q_100": Q_100,
        "F_4": F_4,
        "Q_200": Q_200,
        "F_5": F_5,
        "F_2": F_2,
        "F_100": F_100,
    }

    return variables


class EvaporationProcessEnv(gym.Env[np.ndarray, Union[int, np.ndarray]]):
    def __init__(
        self,
        min_action: np.ndarray = np.array([100.0, 100.0]),
        max_action: np.ndarray = np.array([400, 400]),
        min_observation: np.ndarray = np.array([25, 40]),
        max_observation: np.ndarray = np.array([100, 80]),
        param: dict[float] = {
            "a": 0.5616,
            "b": 0.3126,
            "c": 48.43,
            "d": 0.507,
            "e": 55.0,
            "f": 0.1538,
            "g": 90.0,
            "h": 0.16,
            "M": 20.0,
            "C": 4.0,
            "U_A2": 6.84,
            "C_p": 0.07,
            "lam": 38.5,
            "lam_s": 36.6,
            "F_1": 10.0,
            "X_1": 5.0,
            "F_3": 50.0,
            "T_1": 40.0,
            "T_200": 25.0,
        },
        step_size: float = 1e0,
    ):
        self.step_size = step_size
        self.param = param

        self.action_space = gym.spaces.Box(low=min_action, high=max_action)

        self.observation_space = gym.spaces.Box(min_observation, max_observation)

        self.state = None

        self.algebraic_variables = None

    def step(self, action):
        assert self.action_space.contains(action), f"{action!r} ({type(action)}) invalid"
        assert self.state is not None, "Call reset before using step method."

        # print("self.state:", self.state)
        self.state = erk4_step(compute_f_expl, self.state, action, self.param, self.step_size)
        # print("self.state:", self.state)

        # reward = self._reward_fn(self.state, action)
        reward = 0

        return np.array(self.state, dtype=np.float32), reward, False, False, {}

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ):
        super().reset(seed=seed)

        # self.state = np.array([25, 49.743], dtype=np.float32)
        self.state = np.array([40, 60.0], dtype=np.float32)

        return self.state, {}

    def _reward_fn(self, state, action):
        algebraic_variables = compute_algebraic_variables(state, action, self.param)

        self.algebraic_variables = algebraic_variables

        F_2 = algebraic_variables["F_2"]
        F_3 = self.param["F_3"]
        F_100 = algebraic_variables["F_100"]
        F_200 = action[1]

        return 10.09 * (F_2 + F_3) + 600.0 * F_100 + 0.6 * F_200

    def get(self, key):
        if key in self.algebraic_variables.keys():
            return self.algebraic_variables[key]
        elif key in self.param.keys():
            return self.param[key]