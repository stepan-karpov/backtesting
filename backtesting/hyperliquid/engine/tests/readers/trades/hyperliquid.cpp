#include "../../../readers/trades/hyperliquid.hpp"

#include <cassert>
#include <filesystem>
#include <iostream>

namespace {

std::filesystem::path StaticDirectory() {
    return std::filesystem::path(__FILE__).parent_path() / "static";
}

static const char kFirstFileLine[]  = R"JSON({"user":"0x69d1652ae43f819e7518f732b2ea6b1a8ad00336","coin":"SOL","px":83.168,"sz":12.02,"side":"B","time":"2026-04-01T00:00:04.723000","startPosition":2848.6,"dir":"Open Long","closedPnl":0.0,"hash":"0x225687b4806261a323d00438225182021ec4009a1b658075c61f33073f663b8d","oid":366968523357,"crossed":false,"fee":0.101967,"tid":483694996325267,"cloid":null,"feeToken":"USDC","twapId":null,"builder":null,"builderFee":null,"deployerFee":null,"__index_level_0__":3084})JSON";
static const char kSecondFileLine[] = R"JSON({"user":"0xf5d81a135f756ca16544e53c20fc20643ec3ad53","coin":"SOL","px":83.366,"sz":0.14,"side":"B","time":"2026-04-01T01:00:00.140000","startPosition":6.54,"dir":"Open Long","closedPnl":0.0,"hash":"0xa05462c140b37599a1ce043823158702033800a6dbb6946b441d0e13ffb74f84","oid":367015942592,"crossed":true,"fee":0.00196,"tid":777816937404825,"cloid":"0xfdc527562ddc31d5a7fbe207c20d9605","feeToken":"USDC","twapId":null,"builderFee":null,"deployerFee":null,"liquidation":false,"builder":null,"liquidationMarkPx":null,"liquidationMethod":null,"liquidatedUser":null,"__index_level_0__":40})JSON";

void TestTradesFileReader() {
  const auto dir = StaticDirectory();
  const auto p1  = dir / "00.lz4";

  TradesFileReader file_reader(p1.string());

  int i = 0;
  auto current_line = file_reader.next();
  while (current_line.has_value()) {
    if (i == 0) {
      assert(current_line.value() == kFirstFileLine);
    }
    current_line = file_reader.next();
    ++i;
  }
  assert(i == 6496);
  std::cout << "TestTradesFileReader passed\n";
}

void TestTradesReader() {
  const auto dir = StaticDirectory();
  const auto p1  = dir / "00.lz4";
  const auto p2  = dir / "01.lz4";

  TradesReader files_reader({p1.string(), p2.string()});

  int i = 0;
  auto current_line = files_reader.next();
  while (current_line.has_value()) {
    if (i == 0) {
      assert(current_line.value() == kFirstFileLine);
    }
    if (i == 6497) {
      assert(current_line.value() == kSecondFileLine);
    }
    current_line = files_reader.next();
    ++i;
  }
  assert(i == 13358);
  std::cout << "TestTradesReader passed\n";
}

} // namespace

int main() {
  TestTradesFileReader();
  TestTradesReader();
}
