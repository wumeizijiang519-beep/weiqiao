"""Minimal test entrypoint for runtime images that do not bundle pytest."""

import test_deployment
import test_online_contract
import test_scheduler


def main():
    modules = (test_deployment, test_online_contract, test_scheduler)
    total = 0
    for module in modules:
        for name in sorted(dir(module)):
            if name.startswith("test_"):
                getattr(module, name)()
                total += 1
    print(f"SIMPLEWAM_ONLINE_CONTRACT_TESTS_PASS tests={total}")


if __name__ == "__main__":
    main()
