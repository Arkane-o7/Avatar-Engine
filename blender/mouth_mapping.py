from __future__ import annotations

RHU_BARBS = ("A", "B", "C", "D", "E", "F", "G", "H", "X")

TEXTURE_MOUTH_MAP: dict[str, str] = {
    "A": "mouth_A_closed.png",
    "B": "mouth_B_m_b_p.png",
    "C": "mouth_C_ee.png",
    "D": "mouth_D_aa.png",
    "E": "mouth_E_oh.png",
    "F": "mouth_F_oo.png",
    "G": "mouth_G_f_v.png",
    "H": "mouth_H_l_th.png",
    "X": "mouth_X_rest.png",
}

SHAPE_KEY_MOUTH_MAP: dict[str, str] = {
    "A": "mouth_closed",
    "B": "mouth_mbp",
    "C": "mouth_ee",
    "D": "mouth_aa",
    "E": "mouth_oh",
    "F": "mouth_oo",
    "G": "mouth_fv",
    "H": "mouth_lth",
    "X": "mouth_rest",
}

MOUTH_CUE_INDEX: dict[str, int] = {cue: index for index, cue in enumerate(RHU_BARBS)}


def texture_for_cue(cue: str) -> str:
    return TEXTURE_MOUTH_MAP.get(cue.upper(), TEXTURE_MOUTH_MAP["X"])


def shape_key_for_cue(cue: str) -> str:
    return SHAPE_KEY_MOUTH_MAP.get(cue.upper(), SHAPE_KEY_MOUTH_MAP["X"])
