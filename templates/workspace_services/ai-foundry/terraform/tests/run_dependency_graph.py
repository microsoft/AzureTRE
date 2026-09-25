"""Check the default Terraform graph without initialising an Azure backend.

Run after `terraform init -backend=false`. Reuse its modules and providers.
Only the temporary configuration has its backend removed.
"""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def check_graph(source):
    with tempfile.TemporaryDirectory(prefix="foundry-graph-") as directory:
        offline = Path(directory)
        for path in source.glob("*.tf"):
            shutil.copy2(path, offline / path.name)
        shutil.copy2(source / ".terraform.lock.hcl", offline)
        main = offline / "main.tf"
        backend = '  backend "azurerm" {}\n'
        content = main.read_text()
        if content.count(backend) != 1:
            raise ValueError("Expected one empty AzureRM backend block in main.tf")
        main.write_text(content.replace(backend, "", 1))

        # Link only installed code, never backend metadata or Terraform state.
        (offline / ".terraform").mkdir()
        for name in ("modules", "providers"):
            (offline / ".terraform" / name).symlink_to(
                (source / ".terraform" / name).resolve(strict=True), target_is_directory=True)

        graph = offline / "graph.dot"
        with graph.open("w") as output:
            # The checker accepts the default graph, without -type=plan.
            subprocess.run(["terraform", "graph"], cwd=offline, stdout=output, check=True)
        subprocess.run([sys.executable, str(source / "tests/check_dependency_graph.py"), str(graph)], check=True)


if __name__ == "__main__":
    check_graph(Path(__file__).resolve().parents[1])
