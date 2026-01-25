# gem5 Practice Configuration

This repository contains custom gem5 configurations and practice assignments.

## Prerequisites

For detailed information, please refer to the official [Building gem5](https://www.gem5.org/documentation/general_docs/building) documentation.

**Note:** This setup is designed for Ubuntu 24. If you're using macOS, you'll need to set up an Ubuntu 24 virtual machine.

## Setup Instructions

### 1. Install Dependencies

Install all required packages on Ubuntu:

```bash
sudo apt install build-essential scons python3-dev git pre-commit zlib1g zlib1g-dev \
    libprotobuf-dev protobuf-compiler libprotoc-dev libgoogle-perftools-dev \
    libboost-all-dev libhdf5-serial-dev python3-pydot python3-venv python3-tk mypy \
    m4 libcapstone-dev libpng-dev libelf-dev pkg-config wget cmake doxygen clang-format
```

### 2. Clone and Build gem5

```bash
cd ~
git clone https://github.com/gem5/gem5
cd gem5
scons build/X86/gem5.opt -j$(nproc)
```

**Note:** Building gem5 may take a while depending on your system.

### 3. Install Practice Configurations

Clone this repository into the gem5 configs directory:

```bash
cd ~/gem5/configs
git clone https://github.com/SammySheu/gem5_practice.git
```

**Important:** This repository uses `practice` as the directory name instead of `gem5_practice`. To match the expected structure, rename the cloned directory:

```bash
mv ~/gem5/configs/gem5_practice ~/gem5/configs/practice
```

## Working with Assignments

Each assignment has its own `README.md` file with detailed documentation and instructions. Please refer to the individual assignment folders for specific information.

## Directory Structure

```
~/gem5/configs/practice/
├── Assignment1/
├── Assignment2/
├── Assignment3/
└── ...
```