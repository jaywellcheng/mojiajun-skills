#!/usr/bin/env python3
"""快捷方式指向实际的 backlog-manager.py"""
import sys
import os
sys.path.insert(0, os.path.expanduser("~/.hermes/backlog"))
from backlog_manager import main
main()
