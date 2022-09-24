"""
This file handles parsing of command line arguments
"""
import argparse

parser = argparse.ArgumentParser(description='Update all dependencies')
_ = parser.add_argument('--check-all-compatibility', dest='check_all_compatibility', action="store_true", default=False,
                        help='Check all compatibilities for all dependencies')
_ = parser.add_argument('--redownload', dest='redownload', type=str, default="none",
                        help="Software to force redownload; ALL / software")
_ = parser.add_argument('--skip-dependency-check', dest='skip_dependency_check', action="store_true", default=False,
                        help="Skip looking for new software builds (for testing)")
args = parser.parse_args()
