"""Start full, local, evidence-indexing backend within Android process."""
import importlib.util
import os
import sys

def run_server(base_dir):
    root = os.path.join(base_dir, 'backend')
    os.environ['HISTORYTOOL_DATA_DIR'] = os.path.join(base_dir, 'user_data')
    os.makedirs(os.environ['HISTORYTOOL_DATA_DIR'], exist_ok=True)
    if root not in sys.path:
        sys.path.insert(0, root)
    os.chdir(root)
    import uvicorn
    spec = importlib.util.spec_from_file_location('historytool_server', os.path.join(root, 'app.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules['historytool_server'] = module
    spec.loader.exec_module(module)
    config = uvicorn.Config(module.app, host='127.0.0.1', port=8765, access_log=False, log_level='warning', lifespan='off')
    uvicorn.Server(config).run()
