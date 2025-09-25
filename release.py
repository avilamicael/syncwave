import re, os, sys
from datetime import date
import subprocess


CHANGELOG_FILE = "CHANGELOG.md"
SETTINGS_FILE = "crm/djangoapp/project/settings.py"


def get_current_version():
    with open(SETTINGS_FILE, 'r') as f:
        for line in f:
            if line.startswith("APP_VERSION"):
                return line.split("=")[1].strip().strip('"').strip("'")
    return "0.0.0"


def bump_version(current_version, tipo):
    major, minor, patch = map(int, current_version.split("."))
    if tipo == "major":
        return f"{major+1}.0.0"
    elif tipo == "minor":
        return f"{major}.{minor+1}.0"
    elif tipo == "patch":
        return f"{major}.{minor}.{patch+1}"
    else:
        raise ValueError("Tipo inválido")


def prompt_section(title):
    print(f"\n📝 {title}")
    print("Digite cada item e pressione Enter. Pressione Enter vazio para finalizar.")
    items = []
    while True:
        item = input("- ")
        if not item.strip():
            break
        items.append(item.strip())
    return items


def update_changelog(new_version, sections):
    today = date.today().strftime("%Y-%m-%d")
    entry = f"\n## [{new_version}] - {today}\n"
    for title, itens in sections.items():
        if itens:
            entry += f"### {title}\n"
            for item in itens:
                entry += f"- {item}\n"
            entry += "\n"

    with open(CHANGELOG_FILE, "r+", encoding="utf-8") as f:
        content = f.read()
        f.seek(0)
        f.write("# 📦 Changelog - SyncWave\n\n" + entry + content)


def update_settings_version(new_version):
    with open(SETTINGS_FILE, "r+", encoding="utf-8") as f:
        content = f.read()
        content = re.sub(r'APP_VERSION\s*=\s*["\'].*?["\']', f'APP_VERSION = "{new_version}"', content)
        f.seek(0)
        f.write(content)
        f.truncate()


def main():
    current_version = get_current_version()
    print(f"📌 Versão atual: {current_version}")
    tipo = input("👉 Tipo de versão [major, minor, patch]: ").strip().lower()
    new_version = bump_version(current_version, tipo)

    sections = {
        "Adicionado": prompt_section("Adicionado"),
        "Alterado": prompt_section("Alterado"),
        "Corrigido": prompt_section("Corrigido"),
    }

    print(f"\n✅ Nova versão: {new_version}")

    update_changelog(new_version, sections)
    update_settings_version(new_version)

    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", f"chore(release): v{new_version}"])
    subprocess.run(["git", "tag", f"v{new_version}"])
    subprocess.run(["git", "push"])
    subprocess.run(["git", "push", "--tags"])

    print("\n🚀 Versão publicada com sucesso!")

    # Chama o llm.py
    llm_path = os.path.join(os.path.dirname(__file__), "crm/llm.py")
    print("\n🔗 Chamando llm.py...")
    subprocess.run([sys.executable, llm_path])

if __name__ == "__main__":
    main()
