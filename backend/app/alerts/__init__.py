"""Intelligent fuel-alert system.

An isolated top-layer package: it consumes the *public outputs* of the
recommendation, prediction, pricing and AI layers but never imports their
internals, and nothing in those layers imports alerts back. Alert failures are
contained and degrade gracefully — they never affect core endpoints.
"""
