# Maintainer: Manuel Bleichner <mbleichner AT gmail DOT com>
pkgname=python-koti
pkgver=0.1.0.8da1e08
pkgrel=1
pkgdesc="Declarative configuration manager"
arch=("any")
url="https://github.com/mbleichner/koti"
license=("GPL3")
depends=("python" "pacman" "systemd" "git")
makedepends=("python-setuptools" "python-build" "python-installer" "python-wheel")
optdepends=()
source=("git+https://github.com/mbleichner/koti")
sha256sums=(SKIP)

build() {
    cd "koti"
    python -m build --wheel --no-isolation
}

package() {
    cd "koti"
    python -m installer --destdir="$pkgdir" dist/*.whl
}

pkgver() {
  cd "$srcdir/$pkgname"
  echo "0.1.0.$(git rev-parse --short HEAD)"
}
