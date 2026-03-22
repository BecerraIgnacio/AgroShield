"""Build curated pathogen-crop mapping database with real scientific data."""

from __future__ import annotations

import json
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

PATHOGENS: list[dict] = [
    {
        "name": "Fusarium oxysporum",
        "kingdom": "fungi",
        "crops": ["tomato", "banana", "cotton", "melon", "basil", "chickpea"],
        "diseases": ["Fusarium wilt", "Panama disease"],
        "economic_impact": "Causes >$1 billion annual losses worldwide. Panama disease (race TR4) threatens global banana production.",
        "description": "Soil-borne fungal pathogen that colonizes root vasculature, blocking water transport. Produces mycotoxins including fumonisins. Over 120 host-specific formae speciales.",
        "gram_type": None,
        "cell_wall": "chitin/glucan",
        "optimal_temp_c": [25, 28],
        "transmission": "soil-borne, seed-borne",
    },
    {
        "name": "Xanthomonas campestris",
        "kingdom": "bacteria",
        "crops": ["citrus", "cabbage", "broccoli", "cauliflower", "pepper", "rice"],
        "diseases": ["citrus canker", "black rot of brassicas", "bacterial spot"],
        "economic_impact": "Citrus canker alone causes >$100M annual losses. Major quarantine pathogen in citrus-producing regions.",
        "description": "Gram-negative rod-shaped bacterium. Uses type III secretion system to inject effector proteins into host cells. Multiple pathovars with distinct host ranges.",
        "gram_type": "negative",
        "cell_wall": "lipopolysaccharide outer membrane",
        "optimal_temp_c": [25, 30],
        "transmission": "rain splash, wind-driven rain, contaminated tools",
    },
    {
        "name": "Botrytis cinerea",
        "kingdom": "fungi",
        "crops": ["grape", "strawberry", "tomato", "lettuce", "raspberry", "blueberry"],
        "diseases": ["grey mold", "noble rot (in wine grapes)"],
        "economic_impact": "Pre- and post-harvest losses exceed $10 billion annually worldwide. #2 most important plant pathogen globally.",
        "description": "Necrotrophic fungal pathogen with exceptionally broad host range (>200 plant species). Produces botrydial and botcinins as phytotoxins. Highly adaptable with frequent fungicide resistance.",
        "gram_type": None,
        "cell_wall": "chitin/glucan",
        "optimal_temp_c": [18, 23],
        "transmission": "airborne conidia, contact, wound infection",
    },
    {
        "name": "Pseudomonas syringae",
        "kingdom": "bacteria",
        "crops": ["tomato", "bean", "cherry", "kiwi", "olive", "soybean"],
        "diseases": ["bacterial speck", "bacterial blight", "halo blight"],
        "economic_impact": "Causes 20-30% yield losses in affected tomato and bean crops. Emerging threat to kiwifruit (pv. actinidiae).",
        "description": "Gram-negative bacterium, model organism for plant-pathogen interaction studies. Produces coronatine (jasmonate mimic) and uses ice nucleation to damage plants. Over 60 pathovars.",
        "gram_type": "negative",
        "cell_wall": "lipopolysaccharide outer membrane",
        "optimal_temp_c": [20, 25],
        "transmission": "rain splash, aerosol, contaminated seed",
    },
    {
        "name": "Magnaporthe oryzae",
        "kingdom": "fungi",
        "crops": ["rice", "wheat", "barley", "millet", "ryegrass"],
        "diseases": ["rice blast", "wheat blast"],
        "economic_impact": "Destroys enough rice annually to feed 60 million people. Most destructive rice disease globally. Wheat blast emerging in South America and South Asia.",
        "description": "Hemibiotrophic fungal pathogen. Forms specialized infection structures (appressoria) generating 8 MPa turgor pressure to penetrate host cuticle. Genome extensively studied for effector biology.",
        "gram_type": None,
        "cell_wall": "chitin/melanin",
        "optimal_temp_c": [25, 28],
        "transmission": "airborne conidia, seed-borne",
    },
    {
        "name": "Puccinia graminis",
        "kingdom": "fungi",
        "crops": ["wheat", "barley", "oat", "rye", "triticale"],
        "diseases": ["stem rust", "black rust"],
        "economic_impact": "Historically caused famines. Race Ug99 threatens global wheat production ($60B crop). Capable of 100% yield loss in susceptible varieties.",
        "description": "Obligate biotrophic rust fungus with complex life cycle requiring two hosts (cereal + barberry). Produces urediniospores that can travel thousands of kilometers via wind. Cannot be cultured in vitro.",
        "gram_type": None,
        "cell_wall": "chitin/glucan",
        "optimal_temp_c": [20, 25],
        "transmission": "airborne urediniospores, long-distance wind dispersal",
    },
    {
        "name": "Ralstonia solanacearum",
        "kingdom": "bacteria",
        "crops": ["potato", "tomato", "banana", "tobacco", "eggplant", "ginger"],
        "diseases": ["bacterial wilt", "brown rot of potato"],
        "economic_impact": "Affects >200 plant species across 50 families. Potato brown rot causes major losses in tropical/subtropical regions. Quarantine pathogen in EU.",
        "description": "Gram-negative soil-borne bacterium, species complex with enormous genetic diversity. Enters roots through wounds, colonizes xylem producing extracellular polysaccharides that block water flow. Survives in water and soil for years.",
        "gram_type": "negative",
        "cell_wall": "lipopolysaccharide outer membrane",
        "optimal_temp_c": [27, 35],
        "transmission": "soil-borne, water-borne, infected seed tubers",
    },
    {
        "name": "Erwinia amylovora",
        "kingdom": "bacteria",
        "crops": ["apple", "pear", "quince", "loquat", "hawthorn"],
        "diseases": ["fire blight"],
        "economic_impact": "Most devastating disease of apple and pear. Single outbreaks can destroy entire orchards. Cost the US apple industry >$100M in the 2000s.",
        "description": "Gram-negative enterobacterium. First bacterium ever shown to cause plant disease (1878). Produces amylovoran exopolysaccharide and harpin (type III effector). Spreads rapidly via pollinating insects.",
        "gram_type": "negative",
        "cell_wall": "lipopolysaccharide outer membrane",
        "optimal_temp_c": [24, 28],
        "transmission": "insect vectors (bees), rain splash, pruning tools",
    },
    {
        "name": "Phytophthora infestans",
        "kingdom": "oomycete",
        "crops": ["potato", "tomato", "pepper", "petunia"],
        "diseases": ["late blight"],
        "economic_impact": "Caused the Irish Potato Famine (1845-49). Still causes >$6 billion annual losses globally. Most costly pathogen of potato.",
        "description": "Oomycete (not a true fungus — belongs to Stramenopiles). Produces motile zoospores. Extremely rapid disease cycle — can destroy a field in days under favorable conditions. Evolves rapidly, overcoming resistance genes.",
        "gram_type": None,
        "cell_wall": "cellulose (not chitin)",
        "optimal_temp_c": [15, 20],
        "transmission": "airborne sporangia, soil-borne oospores, infected tubers",
    },
    {
        "name": "Sclerotinia sclerotiorum",
        "kingdom": "fungi",
        "crops": ["soybean", "canola", "sunflower", "lettuce", "carrot", "bean"],
        "diseases": ["white mold", "Sclerotinia stem rot"],
        "economic_impact": "Affects >400 plant species. Causes >$200M annual losses in US soybean alone. Major problem in canola worldwide.",
        "description": "Necrotrophic fungal pathogen producing oxalic acid to suppress host defenses and kill tissue. Forms melanized sclerotia that persist in soil for 5-8 years. No known complete resistance in most crops.",
        "gram_type": None,
        "cell_wall": "chitin/glucan",
        "optimal_temp_c": [15, 22],
        "transmission": "airborne ascospores from soil-borne sclerotia",
    },
    {
        "name": "Colletotrichum gloeosporioides",
        "kingdom": "fungi",
        "crops": ["mango", "avocado", "papaya", "coffee", "citrus", "strawberry"],
        "diseases": ["anthracnose"],
        "economic_impact": "Major pre- and post-harvest disease in tropical/subtropical fruits. Causes 10-80% losses depending on crop and region.",
        "description": "Hemibiotrophic fungal pathogen causing anthracnose. Forms melanized appressoria for host penetration. Part of a species complex with cryptic species. Quiescent infections activate during fruit ripening.",
        "gram_type": None,
        "cell_wall": "chitin/melanin",
        "optimal_temp_c": [25, 30],
        "transmission": "rain splash of conidia, latent infections in flowers/fruits",
    },
]


def build_pathogen_crop_map() -> dict[str, dict]:
    """Build pathogen-crop mapping dictionary keyed by pathogen name."""
    return {p["name"]: {k: v for k, v in p.items() if k != "name"} for p in PATHOGENS}


def save_pathogen_db(output_path: Path | None = None) -> Path:
    """Save pathogen-crop mapping to JSON file."""
    out = output_path or PROCESSED_DIR / "pathogen_crop_map.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    mapping = build_pathogen_crop_map()
    out.write_text(
        json.dumps(mapping, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out


def main() -> None:
    save_pathogen_db()


if __name__ == "__main__":
    main()
