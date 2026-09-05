"""Fail loudly if native ROCm cannot execute the kernels required by Klein."""
import json
import time
import torch
import torch.nn.functional as F

assert torch.version.hip, "This is not a ROCm PyTorch build"
assert torch.cuda.is_available(), "ROCm GPU unavailable"
device = torch.cuda.get_device_properties(0)
assert device.gcnArchName.startswith("gfx1100"), device
torch.manual_seed(123)
start = time.monotonic()
torch.cuda.reset_peak_memory_stats()
with torch.inference_mode():
    a = torch.randn(1024, 1024, device="cuda", dtype=torch.bfloat16)
    product = a @ a.T
    assert torch.isfinite(product).all().item(), "BF16 matmul is non-finite"
    torch.testing.assert_close(product[:8, :8].float().cpu(),
                               a[:8].float().cpu() @ a[:8].float().cpu().T,
                               rtol=0.02, atol=0.5)
    q = torch.randn(1, 8, 256, 128, device="cuda", dtype=torch.bfloat16)
    attn = F.scaled_dot_product_attention(q, q, q)
    assert torch.isfinite(attn).all().item(), "Attention is non-finite"
    pixels = torch.randn(1, 32, 64, 64, device="cuda")
    weights = torch.randn(32, 32, 3, 3, device="cuda")
    conv = F.conv2d(pixels, weights, padding=1)
    assert torch.isfinite(conv).all().item(), "VAE-style convolution is non-finite"
torch.cuda.synchronize()
print(json.dumps({"torch": torch.__version__, "hip": torch.version.hip,
                  "gpu": device.name, "architecture": device.gcnArchName,
                  "vram_bytes": device.total_memory,
                  "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                  "seconds": time.monotonic() - start, "passed": True}, indent=2))
