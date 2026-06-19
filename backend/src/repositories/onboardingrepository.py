"""
onboardingrepository.py
레이어: Repository
역할: 하위 호환 파사드 — 실제 구현은 onboardingscoperepository / onboardinginputrepository에 있음.
"""
from __future__ import annotations

from src.repositories.onboardingscoperepository import *  # noqa: F401,F403
from src.repositories.onboardinginputrepository import *  # noqa: F401,F403
from src.repositories.onboardingapprovalrepository import *  # noqa: F401,F403
