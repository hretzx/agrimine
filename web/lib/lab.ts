/**
 * Links into the Streamlit technical lab (teachers-lab/). The API starts the lab next to itself and says where it is
 * (GET /api/lab: `available`, `url`), so nothing is hard-coded here. Each algorithm's page name is the lab's own address
 * (tests/test_lab_links.py keeps this list equal to the lab's pages).
 */

/** algorithm key (see ALGOS on the For teachers page) -> the lab page that shows it. Profile match has no lab page. */
export const LAB_PAGE = {
  id3: "crop-advisor",
  nb: "model-council",
  kmeans: "cluster-explorer",
  hier: "hierarchical",
  apriori: "pattern-mining",
  fp: "fp-growth-and-eclat",
  regression: "water-lab",
} as const;

/** `labLink("http://localhost:8501", "crop-advisor", 4)` -> "http://localhost:8501/crop-advisor?check=4": the lab opens on the same check as the web app. */
export function labLink(base: string, page?: string, checkId?: number) {
  return `${base.replace(/\/$/, "")}${page ? `/${page}` : ""}${checkId ? `?check=${checkId}` : ""}`;
}
