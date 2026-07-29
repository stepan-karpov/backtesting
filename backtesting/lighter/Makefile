PYTHON   := python3
CXX      := clang++
CXXFLAGS := -O3 -march=native -std=c++17 -fPIC -Wall

# Lazy (=) so the pybind11/numpy imports run ONLY when the .so is built, not on
# every `make test` / `make clean` (which would otherwise print an import traceback).
PYBIND    = $(shell $(PYTHON) -c "import pybind11; print(pybind11.get_include())")
NUMPY     = $(shell $(PYTHON) -c "import numpy; print(numpy.get_include())")
PYINC     = $(shell $(PYTHON) -c "import sysconfig; print(sysconfig.get_path('include'))")
SUFFIX   := $(shell $(PYTHON) -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))")

TARGET   := _engine$(SUFFIX)
HEADERS  := engine/orderbook.hpp engine/execution.hpp engine/result.hpp \
            engine/strategy.hpp  engine/reader.hpp    engine/backtester.hpp

# ── unit tests (GoogleTest) ──────────────────────────────────────────────────
# The engine headers are Python-free, so tests link them directly — no pybind.
# The .so is built ONLY after the tests pass (see the .tests_passed prerequisite).
# Requires GoogleTest:  brew install googletest
GTEST_PREFIX := $(shell brew --prefix googletest 2>/dev/null)
TEST_SRC     := $(wildcard tests/*.cpp)
TEST_FLAGS   := -std=c++17 -O1 -Wall -I$(GTEST_PREFIX)/include
TEST_LDFLAGS := -L$(GTEST_PREFIX)/lib -lgtest -lgtest_main

# Build the test binary, run it, then delete it — the binary is never left behind.
# The subshell propagates the test exit code, so a red suite aborts the build.
RUN_TESTS = $(CXX) $(TEST_FLAGS) $(TEST_SRC) $(TEST_LDFLAGS) -o engine_tests && \
            (./engine_tests; s=$$?; rm -f engine_tests; exit $$s)

all: $(TARGET)

# `| test` is an order-only prerequisite: the tests run FRESH on every build (never
# cached), but they don't force a relink — the .so rebuilds only when its own
# sources change. A red suite fails here, so the .so is not (re)built.
$(TARGET): bindings.cpp $(HEADERS) | test
	$(CXX) $(CXXFLAGS) -shared \
		-I$(PYBIND) -I$(NUMPY) -I$(PYINC) \
		-undefined dynamic_lookup \
		bindings.cpp -o $@

# Always compiles, runs, and removes the test binary — no stamp, no caching.
test:
	@$(RUN_TESTS)

clean:
	rm -f _engine*.so _engine*.dylib engine_tests

.PHONY: all test clean
