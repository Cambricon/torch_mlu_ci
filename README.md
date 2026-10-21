# torch_mlu_ci

Continuous integration for torch_mlu, the Cambricon MLU extension for PyTorch.
This repository provides GitHub Actions workflows to check compatibility with
upstream PyTorch changes.

The torch_mlu source used by this CI is maintained in an internal Cambricon
repository.

## PyTorch Integration

The workflows receive upstream PyTorch events through
[Cross-Repository CI Relay (CRCR)](https://github.com/pytorch/crcr-test).
Compatibility checks help identify changes that affect PyTorch functionality
on Cambricon MLU devices.

## Test Coverage

Compatibility checks include:

- Eager execution and operator correctness.
- Distributed execution.
- `torch.compile` compatibility.

The checks selected for each run depend on the upstream changes.

## CI Results

View runs in [GitHub Actions](https://github.com/Cambricon/torch_mlu_ci/actions).
Runs currently report pass/fail status. More detailed test information will be
added in future updates.
