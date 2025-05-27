# Storage for registered models
MODEL_REGISTRY = set()

def register_model(model):
    """Register a model for audit logging"""
    MODEL_REGISTRY.add(model)
    return model  # Allow use as a decorator