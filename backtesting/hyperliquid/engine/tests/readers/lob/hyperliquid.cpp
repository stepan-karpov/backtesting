#include "../../../readers/lob/hyperliquid.hpp"

#include <filesystem>
#include <cassert>
#include <iostream>

namespace {

std::filesystem::path StaticDirectory() {
    return std::filesystem::path(__FILE__).parent_path() / "static";
}

static const char kFirstFileLine[]  = R"JSON({"time":"2026-04-01T00:00:12.669126791","ver_num":1,"raw":{"channel":"l2Book","data":{"coin":"SOL","time":1775001612017,"levels":[[{"px":"83.141","sz":"18.41","n":1},{"px":"83.137","sz":"0.14","n":1},{"px":"83.134","sz":"7.11","n":2},{"px":"83.133","sz":"12.06","n":1},{"px":"83.132","sz":"11.25","n":2},{"px":"83.131","sz":"0.14","n":1},{"px":"83.124","sz":"24.6","n":2},{"px":"83.12","sz":"373.95","n":1},{"px":"83.117","sz":"0.14","n":1},{"px":"83.116","sz":"27.99","n":1},{"px":"83.111","sz":"0.14","n":1},{"px":"83.11","sz":"203.61","n":2},{"px":"83.105","sz":"208.55","n":3},{"px":"83.104","sz":"0.14","n":1},{"px":"83.103","sz":"374.02","n":1},{"px":"83.102","sz":"25.2","n":1},{"px":"83.1","sz":"180.28","n":1},{"px":"83.098","sz":"0.14","n":1},{"px":"83.095","sz":"208.35","n":2},{"px":"83.092","sz":"53.76","n":1}],[{"px":"83.158","sz":"9.04","n":2},{"px":"83.162","sz":"13.23","n":1},{"px":"83.163","sz":"22.01","n":2},{"px":"83.164","sz":"26.46","n":1},{"px":"83.165","sz":"39.69","n":1},{"px":"83.166","sz":"365.54","n":3},{"px":"83.167","sz":"209.23","n":2},{"px":"83.168","sz":"378.77","n":3},{"px":"83.169","sz":"446.81","n":3},{"px":"83.17","sz":"1.55","n":2},{"px":"83.172","sz":"0.83","n":1},{"px":"83.173","sz":"48.86","n":1},{"px":"83.176","sz":"0.14","n":1},{"px":"83.18","sz":"0.85","n":1},{"px":"83.181","sz":"38.76","n":2},{"px":"83.182","sz":"0.14","n":1},{"px":"83.185","sz":"17.36","n":1},{"px":"83.188","sz":"27.88","n":1},{"px":"83.189","sz":"0.14","n":1},{"px":"83.193","sz":"257.27","n":1}]]}}})JSON";
static const char kSecondFileLine[] = R"JSON({"time":"2026-04-01T01:00:02.126609288","ver_num":1,"raw":{"channel":"l2Book","data":{"coin":"SOL","time":1775005200772,"levels":[[{"px":"83.372","sz":"516.92","n":2},{"px":"83.371","sz":"155.92","n":1},{"px":"83.37","sz":"155.93","n":1},{"px":"83.369","sz":"209.9","n":4},{"px":"83.368","sz":"209.9","n":4},{"px":"83.367","sz":"53.97","n":3},{"px":"83.366","sz":"53.97","n":3},{"px":"83.365","sz":"914.05","n":29},{"px":"83.364","sz":"5387.43","n":84},{"px":"83.363","sz":"5592.25","n":86},{"px":"83.362","sz":"5522.33","n":85},{"px":"83.361","sz":"5522.47","n":85},{"px":"83.36","sz":"7164.97","n":100},{"px":"83.359","sz":"6284.98","n":37},{"px":"83.358","sz":"1313.79","n":10},{"px":"83.357","sz":"1075.34","n":3},{"px":"83.356","sz":"164.89","n":1},{"px":"83.355","sz":"917.17","n":2},{"px":"83.354","sz":"64.66","n":2},{"px":"83.353","sz":"185.93","n":2}],[{"px":"83.373","sz":"0.14","n":1},{"px":"83.379","sz":"0.14","n":1},{"px":"83.386","sz":"0.14","n":1},{"px":"83.393","sz":"0.14","n":1},{"px":"83.394","sz":"6.0","n":1},{"px":"83.399","sz":"0.14","n":1},{"px":"83.4","sz":"15.85","n":3},{"px":"83.402","sz":"18.44","n":2},{"px":"83.405","sz":"6.0","n":1},{"px":"83.406","sz":"0.14","n":1},{"px":"83.41","sz":"1.2","n":1},{"px":"83.412","sz":"0.97","n":2},{"px":"83.414","sz":"9.59","n":1},{"px":"83.419","sz":"0.14","n":1},{"px":"83.423","sz":"39.06","n":2},{"px":"83.424","sz":"1.25","n":1},{"px":"83.426","sz":"0.14","n":1},{"px":"83.432","sz":"6.39","n":3},{"px":"83.433","sz":"26.85","n":1},{"px":"83.439","sz":"0.14","n":1}]]}}})JSON";

void TestLobFileReader() {
  const auto dir = StaticDirectory();
  const auto p1  = dir / "00.lz4";

  LobFileReader file_reader(p1.string());

  int i = 0;
  auto current_line = file_reader.next();
  while (current_line.has_value()) {
    if (i == 0) {
      assert(current_line.value() == kFirstFileLine);
    }
    current_line = file_reader.next();
    ++i;
  }
  assert(i == 6633);
  std::cout << "TestLobFileReader passed\n";
}

/** Возвращает false при ошибке (печатает в stderr). */
void TestLobReader() {
  const auto dir = StaticDirectory();
  const auto p1  = dir / "00.lz4";
  const auto p2  = dir / "01.lz4";

  LobReader files_reader({p1.string(), p2.string()});

  int i = 0;
  auto current_line = files_reader.next();
  while (current_line.has_value()) {
    if (i == 0) {
      assert(current_line.value() == kFirstFileLine);
    }
    if (i == 6634) {
      assert(current_line.value() == kSecondFileLine);
    }
    current_line = files_reader.next();
    ++i;
  }
  assert(i == 13273);
  std::cout << "TestLobReader passed\n";
}

} // namespace

int main() {
  TestLobFileReader();
  TestLobReader();
  return 0;
}
