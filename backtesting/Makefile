PYTHON   := python3
CXX      := clang++
CXXFLAGS := -O3 -march=native -std=c++17 -fPIC -Wall

PYBIND   := $(shell $(PYTHON) -c "import pybind11; print(pybind11.get_include())")
NUMPY    := $(shell $(PYTHON) -c "import numpy; print(numpy.get_include())")
PYINC    := $(shell $(PYTHON) -c "import sysconfig; print(sysconfig.get_path('include'))")
SUFFIX   := $(shell $(PYTHON) -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))")

TARGET   := _engine$(SUFFIX)
HEADERS  := engine/orderbook.hpp engine/execution.hpp engine/result.hpp \
            engine/strategy.hpp  engine/reader.hpp    engine/backtester.hpp

$(TARGET): bindings.cpp $(HEADERS)
	$(CXX) $(CXXFLAGS) -shared \
		-I$(PYBIND) -I$(NUMPY) -I$(PYINC) \
		-I/opt/homebrew/include \
		-L/opt/homebrew/lib -llz4 -larrow -lparquet \
		-undefined dynamic_lookup \
		bindings.cpp -o $@

# Юнит-тест читателя LOB (исполняемый файл, без pybind)
TEST_LOB        := test_lob_hyperliquid
TEST_LOB_SRC    := engine/tests/readers/lob/hyperliquid.cpp
TEST_LOB_FLAGS  := -std=c++17 -Wall -O0 -g -Iengine -I/opt/homebrew/include
TEST_LOB_LDFLAGS := -L/opt/homebrew/lib -llz4

$(TEST_LOB): $(TEST_LOB_SRC) engine/readers/lob/hyperliquid.hpp
	$(CXX) $(TEST_LOB_FLAGS) $< -o $@ $(TEST_LOB_LDFLAGS)

test-lob: $(TEST_LOB)
	./$(TEST_LOB)

# Тест читателя trades (lz4 JSONL, как lob)
TEST_TRADES        := test_trades_hyperliquid
TEST_TRADES_SRC    := engine/tests/readers/trades/hyperliquid.cpp
TEST_TRADES_FLAGS  := -std=c++17 -Wall -O0 -g -Iengine -I/opt/homebrew/include
TEST_TRADES_LDFLAGS := -L/opt/homebrew/lib -llz4

$(TEST_TRADES): $(TEST_TRADES_SRC) engine/readers/trades/hyperliquid.hpp
	$(CXX) $(TEST_TRADES_FLAGS) $< -o $@ $(TEST_TRADES_LDFLAGS)

test-trades: $(TEST_TRADES)
	./$(TEST_TRADES)

# Все нативные тесты: добавляй сюда новый бинарник
TEST_BINS := $(TEST_LOB) $(TEST_TRADES)

test: $(TEST_BINS)
	@set -e; for t in $(TEST_BINS); do echo "==> $$t"; ./$$t; done

clean:
	rm -f _engine*.so _engine*.dylib $(TEST_BINS)

.PHONY: clean test test-lob test-trades
