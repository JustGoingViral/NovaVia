"""
NOVA ViA Platform - Setup Configuration
AI-Powered Neuroplasticity-Based Addiction Recovery Platform
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, "r", encoding="utf-8") as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]

setup(
    name="novavia",
    version="1.0.0",
    author="Institute of Applied Integrated Biophysics",
    author_email="info@novavia.com",
    description="AI-Powered Neuroplasticity-Based Addiction Recovery Platform with Multi-Agent Intelligence, Real-Time EEG Analysis, and Precision Medicine Integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JustGoingViral/NovaVia",
    project_urls={
        "Bug Reports": "https://github.com/JustGoingViral/NovaVia/issues",
        "Source": "https://github.com/JustGoingViral/NovaVia",
        "Documentation": "https://github.com/JustGoingViral/NovaVia/blob/main/README.md",
        "Changelog": "https://github.com/JustGoingViral/NovaVia/blob/main/CHANGELOG.md",
        "Interactive Demo": "https://justgoingviral.github.io/NovaVia/",
        "Citation": "https://github.com/JustGoingViral/NovaVia/blob/main/CITATION.cff",
        "Contributors": "https://github.com/JustGoingViral/NovaVia/blob/main/CONTRIBUTORS.md",
    },
    packages=find_packages(exclude=["tests", "tests.*", "*.tests", "*.tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Web Environment",
        "Framework :: FastAPI",
        "Natural Language :: English",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=24.3.0",
            "isort>=5.12.0",
            "pylint>=3.0.3",
            "mypy>=1.7.1",
        ],
        "docs": [
            "sphinx>=7.2.6",
            "sphinx-rtd-theme>=1.3.0",
        ],
    },
    # Console scripts removed - use 'python demo_device_orchestration.py' and 'python -m api.gateway' instead
    entry_points={},
    include_package_data=True,
    package_data={
        "": ["*.yml", "*.yaml", "*.json", "*.txt"],
        "config": ["*.yml", "*.yaml", "*.json"],
        "data": ["*.sql"],
    },
    zip_safe=False,
    keywords=[
        "addiction recovery",
        "neuroplasticity",
        "AI healthcare",
        "medical AI",
        "machine learning",
        "deep learning",
        "artificial intelligence",
        "precision medicine",
        "personalized medicine",
        "computational neuroscience",
        "EEG analysis",
        "brain-computer interface",
        "hyperbaric therapy",
        "PEMF therapy",
        "red light therapy",
        "photobiomodulation",
        "frequency therapy",
        "biohacking",
        "medical device orchestration",
        "multi-agent systems",
        "HIPAA compliant",
        "mental health",
        "substance abuse treatment",
        "substance use disorder",
        "treatment-resistant depression",
        "postpartum depression",
        "ketamine therapy",
        "hydroxynorketamine",
        "HNK",
        "NMDA receptor",
        "BDNF",
        "digital biomarkers",
        "wearable devices",
        "pharmacogenomics",
        "predictive analytics",
        "crisis intervention",
        "suicide prevention",
        "clinical decision support",
        "neurostimulation",
        "transcranial direct current stimulation",
        "repetitive transcranial magnetic stimulation",
        "closed-loop stimulation",
        "metabolomics",
        "microbiome",
        "gut-brain axis",
        "women's health",
        "Python",
        "TensorFlow",
        "PyTorch",
        "FastAPI",
        "open source",
    ],
    platforms=["any"],
)
