# TORRI Research Focus

## Your Research Areas

Based on `config/sources.yml`, TORRI is configured to track:

### Primary Focus
- **Kilonovae** - Electromagnetic counterparts to neutron star mergers
- **Gamma-Ray Bursts (GRBs)** - High-energy transient events
- **High Energy Astrophysics** - General astro-ph.HE papers

### Specific Interests
- **AT2017gfo** - The first kilonova associated with GW170817
- **Neutron star mergers**
- **Multi-messenger astronomy**

## Current Configuration

### arXiv Categories
- `astro-ph.HE` - High Energy Astrophysical Phenomena

### Keywords
- kilonova, kilonovae
- AT2017gfo
- GRB, gamma-ray burst
- neutron star
- merger

### Feeds
1. **General astro-ph.HE** - Latest 50 papers
2. **Kilonova search** - Kilonova-specific papers
3. **GRB search** - GRB-related papers

## Customization

To change your research focus, edit:

### Option 1: Configuration File
Edit `config/sources.yml`:
```yaml
keywords: ["your", "new", "keywords"]
```

### Option 2: Script Directly
Edit `run_daily_report_ollama.py`:
```python
keywords = ["your", "new", "keywords"]
feeds = [
    "https://export.arxiv.org/api/query?search_query=all:YOUR_TOPIC+AND+cat:CATEGORY",
]
```

## Examples

### Change to Exoplanets
```python
keywords = ["exoplanet", "transit", "radial velocity", "TESS"]
feeds = [
    "https://export.arxiv.org/api/query?search_query=cat:astro-ph.EP&max_results=50",
]
```

### Change to Machine Learning
```python
keywords = ["deep learning", "neural network", "transformer"]
feeds = [
    "https://export.arxiv.org/api/query?search_query=cat:cs.LG&max_results=50",
]
```

### Change to Quantum Computing
```python
keywords = ["quantum", "qubit", "entanglement"]
feeds = [
    "https://export.arxiv.org/api/query?search_query=cat:quant-ph&max_results=50",
]
```

## arXiv Category Reference

Common categories:
- `astro-ph.HE` - High Energy Astrophysics
- `astro-ph.EP` - Earth and Planetary Astrophysics
- `astro-ph.GA` - Astrophysics of Galaxies
- `astro-ph.CO` - Cosmology
- `cs.AI` - Artificial Intelligence
- `cs.LG` - Machine Learning
- `physics.optics` - Optics
- `quant-ph` - Quantum Physics

Full list: https://arxiv.org/category_taxonomy

---

**Current Focus:** High Energy Astrophysics, Kilonovae, and GRBs ⚡🌟
