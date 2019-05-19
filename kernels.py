# pylint: disable=no-member, C, not-callable
import torch


def compute_kernel(f, xtr):
    '''
    :param f: neural network with scalar output
    :param xtr: images trainset [P, ...]
    '''
    ktrtr, _, _ = compute_kernels(f, xtr, xtr[:1])
    return ktrtr


def compute_kernels(f, xtr, xte):
    from hessian import gradient

    ktrtr = xtr.new_zeros(len(xtr), len(xtr))
    ktetr = xtr.new_zeros(len(xte), len(xtr))
    ktete = xtr.new_zeros(len(xte), len(xte))

    params = []
    current = []
    for p in sorted(f.parameters(), key=lambda p: p.numel(), reverse=True):
        current.append(p)
        if sum(p.numel() for p in current) > 2e9 // (8 * (len(xtr) + len(xte))):
            if len(current) > 1:
                params.append(current[:-1])
                current = current[-1:]
            else:
                params.append(current)
                current = []
    if len(current) > 0:
        params.append(current)

    for i, p in enumerate(params):
        print("[{}/{}] [len={} numel={}]".format(i, len(params), len(p), sum(x.numel() for x in p)), flush=True)

        jtr = xtr.new_empty(len(xtr), sum(u.numel() for u in p))  # (P, N~)
        jte = xte.new_empty(len(xte), sum(u.numel() for u in p))  # (P, N~)

        for j, x in enumerate(xtr):
            jtr[j] = gradient(f(x[None]), p)  # (N~)

        for j, x in enumerate(xte):
            jte[j] = gradient(f(x[None]), p)  # (N~)

        ktrtr.add_(jtr @ jtr.t())
        ktetr.add_(jte @ jtr.t())
        ktete.add_(jte @ jte.t())
        del jtr, jte

    return ktrtr, ktetr, ktete


def kernel_likelihood(k, y, mu=None):
    '''
    1/P min_a negative log likelihood of (a * k)

    :param k: kernel
    :param y: labels
    '''
    import math
    if mu is not None:
        y = y - mu

    e, _ = k.symeig()
    u, _ = torch.gels(y.view(-1, 1), k)

    ret = 0
    ret += (y * u.flatten()).mean().log()
    ret += e.log().mean()
    ret += 1 + math.log(2 * math.pi)
    return 0.5 * ret
