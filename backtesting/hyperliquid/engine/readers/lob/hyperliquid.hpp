#pragma once

#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <optional>
#include <stdexcept>

#include <lz4frame.h>

// ── Читает одиночный lz4 файл построчно ──────────────────────────────────────

class LobFileReader {
public:
    explicit LobFileReader(const std::string& path) {
        // Читаем весь lz4 файл в буфер
        std::ifstream file(path, std::ios::binary);
        if (!file.is_open()) {
            throw std::runtime_error("Cannot open file: " + path);
        }
        std::vector<char> compressed(
            (std::istreambuf_iterator<char>(file)),
            std::istreambuf_iterator<char>()
        );

        // Декомпрессируем
        size_t decompressed_capacity = compressed.size() * 20;
        std::vector<char> decompressed(decompressed_capacity);

        LZ4F_dctx* ctx = nullptr;
        LZ4F_createDecompressionContext(&ctx, LZ4F_VERSION);

        size_t src_size      = compressed.size();
        size_t dst_size      = decompressed_capacity;
        size_t bytes_written = 0;
        const char* src      = compressed.data();

        while (src_size > 0) {
            size_t dst_remaining = dst_size - bytes_written;
            size_t src_consumed  = src_size;

            LZ4F_decompress(ctx,
                            decompressed.data() + bytes_written, &dst_remaining,
                            src, &src_consumed,
                            nullptr);

            bytes_written += dst_remaining;
            src           += src_consumed;
            src_size      -= src_consumed;
        }

        LZ4F_freeDecompressionContext(ctx);

        stream_ = std::istringstream(std::string(decompressed.data(), bytes_written));
    }

    // Возвращает следующую строку или nullopt если файл закончился
    std::optional<std::string> next() {
        std::string line;
        while (std::getline(stream_, line)) {
            if (!line.empty()) {
                return line;
            }
        }
        return std::nullopt;
    }

private:
    std::istringstream stream_;
};

// ── Агрегирует несколько LobFileReader-ов, выдаёт строки по порядку ──────────

class LobReader {
public:
    explicit LobReader(std::vector<std::string> file_paths)
        : file_paths_(std::move(file_paths))
        , file_index_(0)
    {
        if (!file_paths_.empty()) {
            current_ = std::make_unique<LobFileReader>(file_paths_[file_index_]);
        }
    }

    // Возвращает следующую строку или nullopt если все файлы закончились
    std::optional<std::string> next() {
        while (current_) {
            if (auto line = current_->next()) {
                return line;
            }

            // Текущий файл закончился — переходим к следующему
            ++file_index_;
            if (file_index_ < file_paths_.size()) {
                current_ = std::make_unique<LobFileReader>(file_paths_[file_index_]);
            } else {
                current_ = nullptr;
            }
        }
        return std::nullopt;
    }

private:
    std::vector<std::string>         file_paths_;
    size_t                           file_index_;
    std::unique_ptr<LobFileReader>   current_;
};