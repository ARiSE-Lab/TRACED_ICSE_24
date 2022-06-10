"""
Export coverage results as graphs
"""

import json
from pathlib import Path
import pandas as pd
import tqdm
import sys
from joblib import Parallel, delayed
import traceback
import subprocess
import shutil
import json
from collections import defaultdict
import sys
import logging
from multiprocessing import Pool
import re
import numpy as np

import argparse

filext_to_lang = {
    "c": "C",
    "cpp": "C++",
    "java": "Java",
}
lang_to_filext = {v: k for k, v in filext_to_lang.items()}

def read_file(fpath, result, row):
    with open(fpath) as f:
        lines = f.readlines()
        count = 0
        should_read = False
        for l in lines:
            first_word = l[:l.find(' ')]
            if first_word == "File":
                if should_read:
                    break
                else:
                    if row["submission_id"] + '.' + lang_to_filext[row["language"]] in l:
                        should_read = True
            if should_read:
                if first_word == "Lines":
                    m_line = re.match(r'Lines executed:(.*)% of (.*)', l)
                    result["line_percent"].append(float(m_line.group(1)))
                    result["line_count"].append(float(m_line.group(2)))
                    count += 1
                elif first_word == "Branches":
                    m_branch = re.match(r'Branches executed:(.*)% of (.*)', l)
                    result["branch_percent"].append(float(m_branch.group(1)))
                    result["branch_count"].append(float(m_branch.group(2)))
                    count += 1
                elif first_word == "Taken":
                    m_branch_taken = re.match(r'Taken at least once:(.*)% of (.*)', l)
                    result["branch_taken_percent"].append(float(m_branch_taken.group(1)))
                    result["branch_taken_count"].append(float(m_branch_taken.group(2)))
                    count += 1
                elif first_word == "Calls":
                    m_call = re.match(r'Calls executed:(.*)% of (.*)', l)
                    result["call_percent"].append(float(m_call.group(1)))
                    result["call_count"].append(float(m_call.group(2)))
                    count += 1

def export_coverage(problem_num):
    """
    example coverage stdout:
    Lines executed:73.33% of 15
    Branches executed:80.00% of 10
    Taken at least once:60.00% of 10
    Calls executed:66.67% of 3
    """

    try:
        problem_name = 'p' + str(problem_num).rjust(5, "0")

        df = pd.read_csv(str(out_metadata_dir / f'{problem_name}_coverage.csv'))
        df = df[df["outcome"] == "success"]

        results = {}
        for lang, group in df.groupby("language"):
            cache = counts_dir / (problem_name + "_lang" + lang + ".json")
            if cache.exists():
                with open(cache, 'r') as f:
                    result = json.load(f)
            else:
                result = {
                    "line_percent": [],
                    "branch_percent": [],
                    "branch_taken_percent": [],
                    "call_percent": [],
                    "line_count": [],
                    "branch_count": [],
                    "branch_taken_count": [],
                    "call_count": [],
                    "problem": problem_name,
                    "language": lang,
                }
                for _, row in group.iterrows():
                    row_out_dir = out_dir / row["problem_id"] / row["language"] / row["submission_id"]

                    for i in range(5):
                        fpath = row_out_dir / f"input_{i}.gcov_stdout"
                        if not fpath.exists():
                            # print("not found", fpath)
                            break
                        read_file(fpath, result, row)
                        if count > 4:
                            print(fpath, i)
                with open(cache, 'w') as f:
                    json.dump(result, f)
            results[lang] = result
        return results
    except Exception:
        print("error:", problem_name)
        return {}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    input_dir = Path("../../all_input_output")
    out_dir = Path("instrumented_output")
    out_metadata_dir = Path("instrumented_metadata")
    counts_dir = Path("instrumented_counts")
    counts_dir.mkdir(exist_ok=True)

    avg_all = {"C": defaultdict(list), "C++": defaultdict(list)}
    individual_stat_all = {"C": defaultdict(list), "C++": defaultdict(list)}
    lines_left_all = {"C": [], "C++": []}
    with Pool(8) as pool:
        for result_all in tqdm.tqdm(pool.imap_unordered(export_coverage, range(4053)), "problems"):
            for lang, result in result_all.items():
                if all(i.stat().st_size == 0 for i in (input_dir / result["problem"]).glob("input_*.txt")):
                    print("no input", result["problem"])
                    break
                lang = result["language"]
                del result["language"]
                del result["problem"]
                for key, data in result.items():
                    # avg_all[lang][key].append(np.average(data))
                    individual_stat_all[lang][key] += data
                
                percent_lines_covered = result["line_percent"]
                total_lines = result["line_count"]
                for plc, tl in zip(percent_lines_covered, total_lines):
                    lines_left_all[lang].append((100-plc) / 100 * tl)

    # print(json.dumps(avg_all, indent=2))

    from matplotlib import pyplot as plt
    from matplotlib.lines import Line2D

    for metric in ["line_percent", "branch_percent"]:
        langs = ["C", "C++"]
        datas = []
        for lang in langs:
            data = np.array(individual_stat_all[lang][metric])
            datas.append(data[data < 100])
            
        fig, ax = plt.subplots(figsize=(9,5))
        ax.hist(datas, bins=50, alpha=0.6, histtype='step', linewidth=2, label=langs, density=True)

        # Edit legend to get lines as legend keys instead of the default polygons
        # and sort the legend entries in alphanumeric order
        handles, labels = ax.get_legend_handles_labels()
        leg_entries = {}
        for h, label in zip(handles, labels):
            leg_entries[label] = Line2D([0], [0], color=h.get_facecolor()[:-1],
                                        alpha=h.get_alpha(), lw=h.get_linewidth())
        labels_sorted, lines = zip(*sorted(leg_entries.items()))
        ax.legend(lines, labels_sorted, frameon=True)

        # Remove spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Add annotations
        n_str = ",".join(f"n_{{{lang}}} = {len(individual_stat_all[lang][metric])}" for lang in langs)
        plt.title(f'normalized {metric.split("_")[0]} coverage (100% excluded) ${n_str}$')
        plt.xlabel('% lines covered')
        plt.ylabel('Frequency')

        plt.axvline(np.median(datas[0]), color='orange', linestyle='dashed', linewidth=1)
        plt.axvline(np.median(datas[1]), color='blue', linestyle='dashed', linewidth=1)

        plt.savefig(f"coverage_{metric}.png")
        plt.close()

    import pandas as pd

    datas = {
        "language/metric": [],
        "<100%": [],
        "100%": [],
    }
    percent_100 = []
    percent_less = []
    for lang in langs:
        for metric in ("line_percent", "branch_percent"):
            data = np.array(individual_stat_all[lang][metric])
            datas["language/metric"].append(f'{lang} {metric.split("_")[0]} coverage')
            num_100 = np.sum(data == 100)
            datas["100%"].append(num_100 / len(data) * 100)
            datas["<100%"].append((len(data) - num_100) / len(data) * 100)
    df = pd.DataFrame(datas)

    # fig, ax = plt.subplots(figsize=(15,5))
    df.plot(
        x = 'language/metric',
        kind = 'bar',
        stacked = True,
        title = 'Proportion 100%/<100% by language/metric',
        mark_right = True,
        # color=['green', 'red'],
        # ax=ax,
        )
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"coverage_percentages.png")
    plt.close()


    datas = {
        "language/metric": [],
        "<100%": [],
        "100%": [],
    }
    percent_100 = []
    percent_less = []
    for lang in langs:
        for metric in ("line_percent", "branch_percent"):
            data = np.array(individual_stat_all[lang][metric])
            datas["language/metric"].append(f'{lang} {metric.split("_")[0]} coverage')
            num_100 = np.sum(data == 100)
            datas["100%"].append(num_100)
            datas["<100%"].append((len(data) - num_100))
    df = pd.DataFrame(datas)

    # fig, ax = plt.subplots(figsize=(15,5))
    df.plot(
        x = 'language/metric',
        kind = 'bar',
        stacked = True,
        title = 'Count 100%/<100% by language/metric',
        mark_right = True,
        # color=['green', 'red'],
        # ax=ax,
        )
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"coverage_counts.png")
    plt.close()

    # TODO: plot the "lines left" examples

    # for lang, avg in avg_all.items():
    #     for key, data in avg.items():
    #         data = np.array(data)
    #         for scale in (30, 100):
    #             if key.endswith('percent'):
    #                 data_100 = data[data == 100]
    #                 data_less = data[data < 100]
    #                 plt.hist(data_less, density=False, bins=scale)
    #                 plt.title(f"{lang} {key} 500 projects, 100 subs all inputs\n$n={len(data)}, n_{{100\\%}}={len(data_100)} ({len(data_100) / len(data) * 100:.2f}\\%), n_{{other}}={len(data_less)} ({len(data_less) / len(data) * 100:.2f}\\%)$")
    #                 plt.xlabel(f"{key} (macro avg, < 100% only)")
    #                 plt.axvline(np.median(data_less), color='k', linestyle='dashed', linewidth=1)
    #                 plt.axvline(np.average(data_less), color='r', linestyle='dashed', linewidth=1)
    #                 if scale == 100:
    #                     plt.yscale("log")
    #                     plt.ylabel("count (log 10)")
    #                 else:
    #                     plt.ylabel("count")
    #                 plt.savefig(f'plot{scale}_average_{key}_nonzero_{lang}.png')
    #                 plt.close()
                
    #             plt.hist(data, density=False, bins=scale)
    #             plt.title(f"{lang} {key} 500 projects, 100 subs all inputs n={len(data)}")
    #             plt.xlabel(f"{key} (macro avg)")
    #             plt.axvline(np.median(data), color='k', linestyle='dashed', linewidth=1)
    #             plt.axvline(np.average(data), color='r', linestyle='dashed', linewidth=1)
    #             if scale == 100:
    #                 plt.yscale("log")
    #                 plt.ylabel("count (log 10)")
    #             else:
    #                 plt.ylabel("count")
    #             plt.savefig(f'plot{scale}_average_{key}_{lang}.png')
    #             plt.close()

    # for lang, individual_stat in individual_stat_all.items():
    #     for key, data in individual_stat.items():
    #         data = np.array(data)
    #         for scale in (30, 100):
    #             if key.endswith('percent'):
    #                 data_100 = data[data == 100]
    #                 data_less = data[data < 100]
    #                 plt.hist(data_less, density=False, bins=scale)
    #                 plt.title(f"{lang} {key} 500 projects, 100 subs all inputs\n$n={len(data)}, n_{{100\\%}}={len(data_100)} ({len(data_100) / len(data) * 100:.2f}\\%), n_{{other}}={len(data_less)} ({len(data_less) / len(data) * 100:.2f}\\%)$")
    #                 plt.xlabel(f"{key} (individual program, < 100% only)")
    #                 plt.axvline(np.median(data_less), color='k', linestyle='dashed', linewidth=1)
    #                 plt.axvline(np.average(data_less), color='r', linestyle='dashed', linewidth=1)
                    
    #                 plt.ylabel("count")
    #                 if scale == 100:
    #                     plt.yscale("log")
    #                     plt.ylabel("count (log 10)")
    #                 else:
    #                     plt.ylabel("count")
    #                 plt.savefig(f'plot{scale}_all_{key}_nonzero_{lang}.png')
    #                 plt.close()

    #             plt.hist(data, density=False, bins=scale)
    #             plt.xlabel(f"{key} (individual program)")
    #             plt.axvline(np.median(data), color='k', linestyle='dashed', linewidth=1)
    #             plt.axvline(np.average(data), color='r', linestyle='dashed', linewidth=1)
    #             plt.title(f"{lang} {key} 500 projects, 100 subs all inputs n={len(data)}")

    #             plt.ylabel("count")
    #             if scale == 100:
    #                 plt.yscale("log")
    #                 plt.ylabel("count (log 10)")
    #             else:
    #                 plt.ylabel("count")
    #             plt.savefig(f'plot{scale}_all_{key}_{lang}.png')
    #             plt.close()

    # for lang, data in lines_left_all.items():
    #     data = np.array(data)
    #     for scale in (30, 100):
    #         plt.hist(data, density=False, bins=scale)
    #         plt.axvline(np.median(data), color='k', linestyle='dashed', linewidth=1)
    #         plt.axvline(np.average(data), color='r', linestyle='dashed', linewidth=1)
    #         plt.title(f"{lang} lines left 500 projects, 100 subs all inputs n={len(data)}")
    #         plt.xlabel(f"lines left to cover")
    #         plt.ylabel("count (log 10)")
    #         plt.yscale("log")
    #         plt.savefig(f'plot{scale}_linesleft_{lang}.png')
    #         plt.close()

    #         data_zero = data[data == 0]
    #         data_nonzero = data[data > 0]
    #         plt.hist(data_nonzero, density=False, bins=scale)
    #         plt.axvline(np.median(data_nonzero), color='k', linestyle='dashed', linewidth=1)
    #         plt.axvline(np.average(data_nonzero), color='r', linestyle='dashed', linewidth=1)
    #         plt.title(f"{lang} lines left 500 projects, 100 subs all inputs\n$n={len(data)}, n_{{zero}}={len(data_zero)} ({len(data_zero) / len(data) * 100:.2f}\\%), n_{{nonzero}}={len(data_nonzero)} ({len(data_nonzero) / len(data) * 100:.2f}\\%)$")
    #         plt.xlabel(f"lines left to cover (nonzero values only)")
    #         plt.ylabel("count (log 10)")
    #         plt.yscale("log")
    #         plt.savefig(f'plot{scale}_linesleft_nonzero_{lang}.png')
    #         plt.close()
