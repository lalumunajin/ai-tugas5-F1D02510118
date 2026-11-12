import json
import os
import sys

FILE_BAWAAN = "kb_printer.json"

def muat_kb(path):
    with open(path, encoding="utf-8") as f:
        kb = json.load(f)
    periksa_kb(kb)
    return kb


def periksa_kb(kb):
    aturan = kb["aturan"]
    sumber = kb["sumber"]
    if len(sumber) < 2:
        raise ValueError("Minimal 2 sumber diperlukan.")
    if len(aturan) < 5:
        raise ValueError("Minimal 5 aturan diperlukan.")
    for r in aturan:
        if r["mode"] not in ("dan", "atau"):
            raise ValueError(f"{r['id']}: mode harus 'dan' atau 'atau'.")
        if r["sumber"] not in sumber:
            raise ValueError(f"{r['id']}: sumber {r['sumber']} tidak ada di daftar sumber.")
    if len(kesimpulan_akhir(kb)) < 3:
        raise ValueError("Minimal 3 kesimpulan akhir diperlukan.")


def hasil_antara(kb):
    """Semua fakta yang bisa menjadi hasil aturan."""
    return {r["maka"] for r in kb["aturan"]}


def syarat_semua(kb):
    """Semua fakta yang muncul sebagai syarat aturan."""
    s = set()
    for r in kb["aturan"]:
        s.update(r["jika"])
    return s


def kesimpulan_akhir(kb):
    """Hasil aturan yang tidak dipakai sebagai syarat aturan lain."""
    return hasil_antara(kb) - syarat_semua(kb)


def fakta_pertanyaan(kb):
    """Fakta yang tidak pernah menjadi hasil aturan -> ditanyakan ke user.
    Urutan mengikuti kemunculan pertama di file aturan."""
    hasil = hasil_antara(kb)
    urut = []
    for r in kb["aturan"]:
        for f in r["jika"]:
            if f not in hasil and f not in urut:
                urut.append(f)
    return urut


def syarat_terpenuhi(r, memori):
    if r["mode"] == "dan":
        return all(f in memori for f in r["jika"])
    return any(f in memori for f in r["jika"])


def forward_chaining(kb, fakta_awal):
    """Mengembalikan (memori, asal, riwayat).
    asal    : {hasil: aturan yang menghasilkannya}
    riwayat : daftar (nomor siklus, aturan) yang dijalankan
    """
    memori = set(fakta_awal)
    asal = {}
    riwayat = []
    siklus = 0
    while True:
        cocok = [r for r in kb["aturan"]
                 if syarat_terpenuhi(r, memori) and r["maka"] not in memori]
        if not cocok:
            break
        r = cocok[0]                      
        siklus += 1
        memori.add(r["maka"])
        asal[r["maka"]] = r
        riwayat.append((siklus, r))
    return memori, asal, riwayat, siklus + 1


def tanya(nomor, fakta):
    while True:
        try:
            jawab = input(f"{nomor}. Apakah {fakta}? (y/t) > ").strip().lower()
        except EOFError:
            print()
            sys.exit(1)
        if jawab in ("y", "ya"):
            return True
        if jawab in ("t", "tidak"):
            return False
        print("   Jawab dengan y atau t.")


def cetak_alasan(kb, fakta, memori, asal, indent=2):
    r = asal[fakta]
    ada = [f for f in r["jika"] if f in memori]
    print(f"{' ' * indent}{fakta}  <- {r['id']} ({', '.join(ada)})")
    for f in ada:
        if f in asal:
            cetak_alasan(kb, f, memori, asal, indent + 2)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), FILE_BAWAAN)
    try:
        kb = muat_kb(path)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"Gagal memuat file aturan: {e}")
        sys.exit(1)

    print(kb["judul"])
    print("Jawab y/t.")

    ya = []
    for i, f in enumerate(fakta_pertanyaan(kb), 1):
        if tanya(i, f):
            ya.append(f)

    print()
    print("Fakta awal: " + (", ".join(ya) if ya else "(tidak ada)"))
    print()

    memori, asal, riwayat, terakhir = forward_chaining(kb, ya)
    for no, r in riwayat:
        print(f"Siklus {no}: {r['id']} -> {r['maka']}")
    print(f"Siklus {terakhir}: tidak ada aturan baru, berhenti")
    print()

    akhir = kesimpulan_akhir(kb)
    
    hasil_akhir = [r["maka"] for _, r in riwayat if r["maka"] in akhir]

    if hasil_akhir:
        print("Kesimpulan: " + ", ".join(hasil_akhir))
        print("Alasan:")
        for h in hasil_akhir:
            cetak_alasan(kb, h, memori, asal)
    else:
        print("Kesimpulan: tidak ada")
        antara = [r["maka"] for _, r in riwayat]
        if antara:
            print("Alasan: hanya terbentuk simpulan antara (" + ", ".join(antara)
                  + "), belum cukup untuk kesimpulan akhir.")
        else:
            print("Alasan: tidak ada aturan yang syaratnya terpenuhi oleh jawaban 'ya'.")
    print()
    print("Catatan: " + kb["batas"])


if __name__ == "__main__":
    main()
