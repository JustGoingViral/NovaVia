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
    author="NOVA ViA Systems",
    author_email="info@novavia.com",
    description="AI-Powered Neuroplasticity-Based Addiction Recovery Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JustGoingViral/NovaVia",
    project_urls={
        "Bug Reports": "https://github.com/JustGoingViral/NovaVia/issues",
        "Source": "https://github.com/JustGoingViral/NovaVia",
        "Documentation": "https://github.com/JustGoingViral/NovaVia/blob/main/README.md",
        "Changelog": "https://github.com/JustGoingViral/NovaVia/blob/main/CHANGELOG.md",
    },
    packages=find_packages(exclude=["tests", "tests.*", "*.tests", "*.tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
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
    entry_points={
        "console_scripts": [
            "novavia-demo=demo_device_orchestration:main",
            "novavia-api=api.gateway:main",
        ],
    },
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
        "EEG analysis",
        "treatment coordination",
        "hyperbaric therapy",
        "PEMF therapy",
        "biohacking",
        "medical device orchestration",
        "HIPAA compliant",
        "mental health",
        "substance abuse treatment",
    ],
    platforms=["any"],
)
