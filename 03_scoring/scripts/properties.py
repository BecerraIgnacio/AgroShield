"""Physicochemical property calculator for peptide sequences."""
from __future__ import annotations

from Bio.SeqUtils.ProtParam import ProteinAnalysis
from modlamp.descriptors import PeptideDescriptor


VALID_AAS = set("ACDEFGHIKLMNPQRSTVWY")


def net_charge(sequence: str, pH: float = 7.0) -> float:
    """Net charge at given pH using BioPython."""
    pa = ProteinAnalysis(sequence)
    return pa.charge_at_pH(pH)


def hydrophobic_ratio(sequence: str) -> float:
    """Fraction of hydrophobic residues (AILMFWVP)."""
    hydrophobic = set("AILMFWVP")
    count = sum(1 for aa in sequence if aa in hydrophobic)
    return count / len(sequence)


def instability_index(sequence: str) -> float:
    """Instability index via BioPython ProteinAnalysis."""
    pa = ProteinAnalysis(sequence)
    return pa.instability_index()


def molecular_weight(sequence: str) -> float:
    pa = ProteinAnalysis(sequence)
    return pa.molecular_weight()


def aromaticity(sequence: str) -> float:
    pa = ProteinAnalysis(sequence)
    return pa.aromaticity()


def gravy(sequence: str) -> float:
    """Grand average of hydropathicity."""
    pa = ProteinAnalysis(sequence)
    return pa.gravy()


def hydrophobic_moment(sequence: str) -> float:
    """Hydrophobic moment using modlAMP (Eisenberg scale, window=11)."""
    desc = PeptideDescriptor(sequence, "eisenberg")
    desc.calculate_moment(window=min(11, len(sequence)))
    return float(desc.descriptor[0][0])


def amphipathicity(sequence: str) -> float:
    """Amphipathicity as hydrophobic moment normalized by hydrophobicity."""
    hm = hydrophobic_moment(sequence)
    hr = hydrophobic_ratio(sequence)
    if hr == 0:
        return 0.0
    return hm / hr


def compute_all_properties(sequence: str) -> dict:
    """Compute all physicochemical properties for a sequence."""
    return {
        "charge": net_charge(sequence),
        "hydrophobic_ratio": hydrophobic_ratio(sequence),
        "instability_index": instability_index(sequence),
        "molecular_weight": molecular_weight(sequence),
        "aromaticity": aromaticity(sequence),
        "gravy": gravy(sequence),
        "hydrophobic_moment": hydrophobic_moment(sequence),
    }
