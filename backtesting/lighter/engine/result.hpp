#pragma once
#include "execution.hpp"
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <limits>
#include <string>
#include <vector>

struct RunData {
    std::vector<int64_t> pnl_t;
    std::vector<double>  pnl_v, inv_v;

    std::vector<int64_t> qt_t;
    std::vector<double>  qt_bid, qt_ask, qt_mid;

    std::vector<int64_t> fill_t;
    std::vector<int32_t> fill_side;
    std::vector<double>  fill_price, fill_size, fill_inv, fill_mid;

    // Pre-size the output vectors from counts the Backtester knows up front, so the
    // hot push_back paths don't reallocate. The quote vectors (qt_*) are by far the
    // largest at a small quote_log_stride — reserving them is the main win.
    void reserve(std::size_t n_quotes, std::size_t n_pnl, std::size_t n_fills) {
        qt_t.reserve(n_quotes);
        qt_bid.reserve(n_quotes);
        qt_ask.reserve(n_quotes);
        qt_mid.reserve(n_quotes);
        pnl_t.reserve(n_pnl);
        pnl_v.reserve(n_pnl);
        inv_v.reserve(n_pnl);
        fill_t.reserve(n_fills);
        fill_side.reserve(n_fills);
        fill_price.reserve(n_fills);
        fill_size.reserve(n_fills);
        fill_inv.reserve(n_fills);
        fill_mid.reserve(n_fills);
    }

    // ── write API (called by Backtester) ──────────────────────────────────────

    void add_pnl_snapshot(int64_t t, double pnl, double inv) {
        pnl_t.push_back(t);
        pnl_v.push_back(pnl);
        inv_v.push_back(inv);
    }

    void add_quote(int64_t t,
                   bool has_bid, double bid_price,
                   bool has_ask, double ask_price,
                   double mid) {
        static const double kNaN = std::numeric_limits<double>::quiet_NaN();
        qt_t.push_back(t);
        qt_bid.push_back(has_bid ? bid_price : kNaN);
        qt_ask.push_back(has_ask ? ask_price : kNaN);
        qt_mid.push_back(mid);
    }

    void add_fill(int64_t t, const Fill& f, double inv_after, double mid_at_fill) {
        fill_t.push_back(t);
        fill_side.push_back(f.side);
        fill_price.push_back(f.price);
        fill_size.push_back(f.size);
        fill_inv.push_back(inv_after);
        fill_mid.push_back(mid_at_fill);
    }

    // ── serialisation ─────────────────────────────────────────────────────────
    // Writes three CSV files:
    //   {prefix}_pnl.csv    — t_us, pnl, inventory
    //   {prefix}_quotes.csv — t_us, bid, ask, mid
    //   {prefix}_fills.csv  — t_us, side, price, size, inventory, mid_at_fill

    void save_csv(const std::string& prefix) const {
        static const char* SIDES[] = {"bid", "ask", "markout"};

        // Fast float → string. snprintf("%.12g") reproduces the old
        // setprecision(12) default-float output but skips constructing a
        // std::ostringstream (with its locale machinery) per value — the hot-path
        // antipattern that dominated save_csv. NaN → empty field, as before.
        auto dbl = [](double v) -> std::string {
            if (std::isnan(v)) return "";
            char buf[32];
            const int n = std::snprintf(buf, sizeof buf, "%.12g", v);
            return std::string(buf, n > 0 ? n : 0);
        };

        {
            std::ofstream f(prefix + "_pnl.csv");
            f << "t_us,pnl,inventory\n";
            for (std::size_t i = 0; i < pnl_t.size(); ++i)
                f << pnl_t[i] << ',' << dbl(pnl_v[i]) << ',' << dbl(inv_v[i]) << '\n';
        }
        {
            std::ofstream f(prefix + "_quotes.csv");
            f << "t_us,bid,ask,mid\n";
            for (std::size_t i = 0; i < qt_t.size(); ++i)
                f << qt_t[i] << ','
                  << dbl(qt_bid[i]) << ',' << dbl(qt_ask[i]) << ',' << dbl(qt_mid[i]) << '\n';
        }
        {
            std::ofstream f(prefix + "_fills.csv");
            f << "t_us,side,price,size,inventory,mid_at_fill\n";
            for (std::size_t i = 0; i < fill_t.size(); ++i)
                f << fill_t[i] << ','
                  << SIDES[fill_side[i]] << ','
                  << dbl(fill_price[i]) << ','
                  << dbl(fill_size[i]) << ','
                  << dbl(fill_inv[i]) << ','
                  << dbl(fill_mid[i]) << '\n';
        }
    }
};
