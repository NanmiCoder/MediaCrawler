# RFC: Firefox-based stealth option (proposal)

> Status: Proposal
> Created: 2026-05-26
> Tracking discussion: TBD

## Overview

Optional Firefox-based stealth backend for the Playwright launch path, parallel to the current Chromium-based setup. Selected via config flag, no change to defaults.

## Motivation

Saved-login + Playwright is the project's core technique. Sessions still get flagged by platform fingerprint checks over time. A second engine option with stealth patches at the C++ source level gives operators a fallback when their Chromium-based sessions start getting banned.

## Proposed change

A small switch in the browser launch helper that, when configured, uses `invisible_playwright` instead of standard Playwright. `invisible_playwright` wraps a patched Firefox 150 binary (https://github.com/feder-cr/invisible_firefox, MPL-2, same license as Firefox upstream) where fingerprint randomization happens at the C++ level rather than via JS injection.

Drop-in compatible with the existing `playwright.async_api` usage. Same `BrowserContext`, same login state, same JS expression evaluation.

## Out of scope

No change to default browser. No change to existing login flows. No new platform support. Backend selection is user-driven via config.

## Maintenance

Issues against the backend route to feder-cr/invisible_playwright. Only ask of this repo would be the small launch helper switch plus a config entry.

---

## 简介

可选的 Firefox 浏览器后端，作为现有 Chromium 路径的并行选项。需要在配置中开启，不影响默认行为。完整说明见上方英文部分。
