"""Build report/MP2_Report.pdf from report/report.md with pandoc and pdflatex.

Two transformations are applied before pandoc runs:
- `{{table:name}}` is replaced by output/tables/name.md as a LaTeX longtable whose
  columns never wrap, and `{{float:name|caption}}` by the same table as a compact
  float, so included tables always match the latest analysis run.
- Every captioned pipe table becomes a floating table, so no table is split across
  pages; column widths follow the dash counts of the Markdown separator row.
Run `src/run_all.py` first.
"""

import re
import subprocess

from config import ROOT, TAB_DIR

REPORT_DIR = ROOT / "report"


NUMERIC = re.compile(r"^\(?-?[\d.]+\)?\**$")


def cell(text: str) -> str:
    for ch in "&%#_{}":
        text = text.replace(ch, "\\" + ch)
    text = re.sub(r"(?<![\w.])-(?=[\d.])", r"\\textminus{}", text)  # a minus sign never breaks a line
    return text.replace("χ²", r"$\chi^2$")


def md_to_latex(md: str) -> str:
    """Render a pipe table as a booktabs longtable with non-wrapping columns."""
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in md.splitlines()]
    header, body = rows[0], rows[2:]
    align = "".join("r" if all(NUMERIC.match(r[i]) for r in body if r[i]) else "l"
                    for i in range(len(header)))
    head = " & ".join(cell(h) for h in header) + r" \\"
    lines = [rf"\begin{{longtable}}{{@{{}}{align}@{{}}}}", r"\toprule", head, r"\midrule", r"\endhead"]
    # "{}" stops a cell that starts with "[" being read as an option of the previous "\\".
    lines += ["{}" + " & ".join(cell(c) for c in r) + r" \\" for r in body]
    lines += [r"\bottomrule", r"\end{longtable}"]
    return "```{=latex}\n" + "\n".join(lines) + "\n```"


def inline(text: str) -> str:
    """Convert a Markdown table cell to LaTeX, escaping only outside $...$ math."""
    parts = text.replace("\\*", "*").split("$")
    for i in range(0, len(parts), 2):
        parts[i] = (parts[i].replace("&", r"\&").replace("%", r"\%")
                    .replace("<", r"$<$").replace(">", r"$>$"))
    return "$".join(parts)


def float_table(m: re.Match) -> str:
    lines = m.group("table").strip().splitlines()
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in lines]
    header, seps, body = rows[0], rows[1], rows[2:]
    left = [i for i, sep in enumerate(seps) if not sep.endswith(":")]
    total = sum(len(seps[i]) for i in left)
    spec = ""
    for i, sep in enumerate(seps):
        if i in left:
            share = len(sep) * len(left) / total
            spec += rf">{{\raggedright\arraybackslash\hsize={share:.3f}\hsize}}X"
        else:
            spec += "r"
    out = [r"\begin{table}[htbp]", r"\centering", rf"\caption{{{inline(m.group('caption'))}}}",
           r"\small", rf"\begin{{tabularx}}{{\linewidth}}{{@{{}}{spec}@{{}}}}", r"\toprule",
           " & ".join(inline(c) for c in header) + r" \\", r"\midrule"]
    out += ["{}" + " & ".join(inline(c) for c in r) + r" \\" for r in body]
    out += [r"\bottomrule", r"\end{tabularx}", r"\end{table}"]
    return "```{=latex}\n" + "\n".join(out) + "\n```\n"


def float_tables(text: str) -> str:
    pattern = r"(?P<table>(?:^\|.*\|[ \t]*\n)+)\n?Table: (?P<caption>.+)\n"
    return re.sub(pattern, float_table, text, flags=re.M)


def md_to_float(md: str, caption: str) -> str:
    """Render a generated pipe table as a compact floating table (never split across pages)."""
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in md.splitlines()]
    header, body = rows[0], rows[2:]
    align = "l" + "r" * (len(header) - 1)
    lines = [r"\begin{table}[htbp]", r"\centering", rf"\caption{{{inline(caption)}}}",
             r"\footnotesize\setlength{\tabcolsep}{3.5pt}", rf"\begin{{tabular}}{{@{{}}{align}@{{}}}}",
             r"\toprule", " & ".join(cell(h) for h in header) + r" \\", r"\midrule"]
    lines += ["{}" + " & ".join(cell(c) for c in r) + r" \\" for r in body]
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "```{=latex}\n" + "\n".join(lines) + "\n```"


def include_tables(text: str) -> str:
    def sub(m):
        return md_to_latex((TAB_DIR / f"{m.group(1)}.md").read_text().strip())

    def sub_float(m):
        return md_to_float((TAB_DIR / f"{m.group(1)}.md").read_text().strip(), m.group(2))

    text = re.sub(r"\{\{float:([\w]+)\|([^}]+)\}\}", sub_float, text)
    return re.sub(r"\{\{table:([\w]+)\}\}", sub, text)


def main() -> None:
    rendered = REPORT_DIR / "build" / "report.md"
    rendered.parent.mkdir(exist_ok=True)
    rendered.write_text(include_tables(float_tables((REPORT_DIR / "report.md").read_text())))
    subprocess.run([
        "pandoc", str(rendered), "-o", str(REPORT_DIR / "MP2_Report.pdf"),
        "--pdf-engine=pdflatex", "--number-sections", f"--resource-path={ROOT}",
        "-H", str(REPORT_DIR / "header.tex"),
        "-V", "documentclass=article", "-V", "fontsize=10pt",
        "-V", "geometry:margin=2.2cm", "-V", "colorlinks=false",
    ], check=True)
    print(f"report written to {REPORT_DIR / 'MP2_Report.pdf'}")


if __name__ == "__main__":
    main()
