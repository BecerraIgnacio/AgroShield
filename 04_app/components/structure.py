"""3D structure viewer — helix prediction via 3Dmol.js rendered as HTML component."""

import math

import streamlit as st
import streamlit.components.v1 as st_components

# Tile-style color scheme matching the Scientific Sentinel design system
AA_COLORS = {
    # Positive (blue)
    "K": {"bg": "#dbeafe", "text": "#1d4ed8", "border": "#bfdbfe"},
    "R": {"bg": "#dbeafe", "text": "#1d4ed8", "border": "#bfdbfe"},
    "H": {"bg": "#dbeafe", "text": "#1d4ed8", "border": "#bfdbfe"},
    # Negative (red)
    "D": {"bg": "#fee2e2", "text": "#b91c1c", "border": "#fecaca"},
    "E": {"bg": "#fee2e2", "text": "#b91c1c", "border": "#fecaca"},
    # Hydrophobic (gray)
    "A": {"bg": "#f3f4f6", "text": "#374151", "border": "#e5e7eb"},
    "V": {"bg": "#f3f4f6", "text": "#374151", "border": "#e5e7eb"},
    "I": {"bg": "#f3f4f6", "text": "#374151", "border": "#e5e7eb"},
    "L": {"bg": "#f3f4f6", "text": "#374151", "border": "#e5e7eb"},
    "M": {"bg": "#f3f4f6", "text": "#374151", "border": "#e5e7eb"},
    "F": {"bg": "#f3f4f6", "text": "#374151", "border": "#e5e7eb"},
    "W": {"bg": "#f3f4f6", "text": "#374151", "border": "#e5e7eb"},
    "P": {"bg": "#f3f4f6", "text": "#374151", "border": "#e5e7eb"},
    # Polar (purple)
    "S": {"bg": "#f3e8ff", "text": "#7e22ce", "border": "#e9d5ff"},
    "T": {"bg": "#f3e8ff", "text": "#7e22ce", "border": "#e9d5ff"},
    "N": {"bg": "#f3e8ff", "text": "#7e22ce", "border": "#e9d5ff"},
    "Q": {"bg": "#f3e8ff", "text": "#7e22ce", "border": "#e9d5ff"},
    "Y": {"bg": "#f3e8ff", "text": "#7e22ce", "border": "#e9d5ff"},
    # Cysteine (yellow)
    "C": {"bg": "#fef9c3", "text": "#854d0e", "border": "#fef08a"},
    # Glycine (green)
    "G": {"bg": "#dcfce7", "text": "#15803d", "border": "#bbf7d0"},
}

AA_DEFAULT = {"bg": "#f9fafb", "text": "#6b7280", "border": "#e5e7eb"}


def build_helix_pdb(sequence: str) -> str:
    """Build an idealized alpha-helix PDB from sequence."""
    lines = []
    rise_per_residue = 1.5
    radius = 2.3
    residues_per_turn = 3.6

    for i, aa in enumerate(sequence):
        angle = (2 * math.pi * i) / residues_per_turn
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        z = i * rise_per_residue
        lines.append(
            f"ATOM  {i+1:5d}  CA  ALA A{i+1:4d}    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00           C"
        )
    lines.append("END")
    return "\n".join(lines)


def show_3d_structure(sequence: str, width: int = 700, height: int = 500) -> None:
    pdb_data = build_helix_pdb(sequence)
    pdb_escaped = pdb_data.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")

    html = f"""
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <div id="mol-viewer" style="
        width:{width}px; height:{height}px; position:relative;
        background: #f8fafc; border-radius: 16px;
        border: 1px solid #e2e8f0; overflow: hidden;
        background-image: radial-gradient(rgba(1,45,29,0.03) 1px, transparent 1px);
        background-size: 24px 24px;
    "></div>
    <script>
        var viewer = $3Dmol.createViewer("mol-viewer", {{backgroundColor: "#f8fafc"}});
        viewer.addModel(`{pdb_escaped}`, "pdb");
        viewer.setStyle({{}}, {{cartoon: {{color: "0x012d1d", opacity: 0.85}}}});
        viewer.addStyle({{}}, {{sphere: {{scale: 0.3, colorscheme: "amino"}}}});
        viewer.zoomTo();
        viewer.render();
    </script>
    """
    st_components.html(html, width=width + 20, height=height + 20)


def sequence_annotation(sequence: str) -> str:
    """Return HTML with tile-style color-coded amino acids."""
    parts = [
        '<div style="display: flex; flex-wrap: wrap; gap: 6px; font-family: monospace;">'
    ]
    for aa in sequence:
        colors = AA_COLORS.get(aa, AA_DEFAULT)
        parts.append(
            f'<span style="'
            f"display: inline-flex; align-items: center; justify-content: center; "
            f"width: 36px; height: 36px; border-radius: 6px; "
            f"background: {colors['bg']}; color: {colors['text']}; "
            f"border: 1px solid {colors['border']}; "
            f"font-weight: 700; font-size: 14px; "
            f'box-shadow: 0 1px 2px rgba(0,0,0,0.05);"'
            f' title="{aa}">{aa}</span>'
        )
    parts.append("</div>")
    return "".join(parts)


def sequence_legend() -> str:
    categories = [
        ("#dbeafe", "#bfdbfe", "Positive (K,R,H)"),
        ("#fee2e2", "#fecaca", "Negative (D,E)"),
        ("#f3f4f6", "#e5e7eb", "Hydrophobic"),
        ("#f3e8ff", "#e9d5ff", "Polar (S,T,N,Q,Y)"),
        ("#fef9c3", "#fef08a", "Cysteine"),
        ("#dcfce7", "#bbf7d0", "Glycine"),
    ]
    parts = [
        '<div style="display: flex; flex-wrap: wrap; gap: 16px; margin-top: 16px; '
        'padding-top: 16px; border-top: 1px solid #f1f5f9;">'
    ]
    parts.append(
        '<span style="font-size: 10px; font-weight: 800; color: #94a3b8; '
        "text-transform: uppercase; letter-spacing: 0.05em; width: 100%; "
        'margin-bottom: 4px;">Color Legend</span>'
    )
    for bg, border, label in categories:
        parts.append(
            f'<span style="display: inline-flex; align-items: center; gap: 6px;">'
            f'<span style="width: 12px; height: 12px; border-radius: 50%; '
            f'background: {bg}; border: 1px solid {border};"></span>'
            f'<span style="font-size: 12px; color: #64748b; font-weight: 500;">'
            f"{label}</span></span>"
        )
    parts.append("</div>")
    return "".join(parts)
