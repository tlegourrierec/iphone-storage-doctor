class IphoneStorageDoctor < Formula
  include Language::Python::Virtualenv

  desc "Analyse le stockage d'un iPhone branché en USB et récupère de l'espace"
  homepage "https://github.com/tlegourrierec/iphone-storage-doctor"
  url "file:///Users/thomaslegourrierec/Downloads/iphone-storage-doctor"
  version "1.0.0"
  license "MIT"

  depends_on "python@3.13"
  depends_on "libimobiledevice" => :recommended

  def install
    venv = virtualenv_create(libexec, "python3.13")
    # pymobiledevice3 n'est pas dans homebrew-core : on laisse pip résoudre
    # l'arbre de dépendances dans le venv isolé de la formule.
    system libexec/"bin/pip", "install", "--no-cache-dir", buildpath
    bin.install_symlink libexec/"bin/ipsd"
    bin.install_symlink libexec/"bin/iphone-storage-doctor"
  end

  def caveats
    <<~EOS
      Branche l'iPhone en USB, déverrouille-le et accepte « Se fier à cet
      ordinateur », puis lance :

        ipsd doctor

      Le nettoyage est en simulation par défaut ; « ipsd clean --apply »
      exécute réellement, après avoir copié les fichiers sur le Mac.
    EOS
  end

  test do
    assert_match "1.0.0", shell_output("#{bin}/ipsd --version")
    # Sans appareil branché, la commande doit échouer proprement (code 2)
    # et non planter sur une trace Python.
    output = shell_output("#{bin}/ipsd storage 2>&1", 2)
    refute_match "Traceback", output
  end
end
