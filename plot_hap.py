#!/usr/bin/env alias python3
import os
import sys
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def parse_args():
    parser = argparse.ArgumentParser(description="Plot hap.py summary results.")
    
    # 核心输入：支持传入多个 csv 文件
    parser.add_argument('-i', '--inputs', nargs='+', required=True, 
                        help='Path to multiple hap.py summary.csv files, separated by space.')
    
    # 对应标签
    parser.add_argument('-s', '--sample-ids', nargs='+', required=True,
                        help='Sample IDs corresponding to each input CSV file.')
    parser.add_argument('-t', '--tags', nargs='+', required=True,
                        help='Tags/Methods corresponding to each input CSV file.')
    
    # 过滤条件
    parser.add_argument('--type', type=str, default='SNP', choices=['SNP', 'INDEL'],
                        help='Type to plot: SNP or INDEL (default: SNP)')
    parser.add_argument('--filter', type=str, default='PASS', choices=['PASS', 'ALL'],
                        help='Filter to plot: PASS or ALL (default: PASS)')
    
    # 输出文件
    parser.add_argument('-o', '--output', type=str, default='hap_summary_plot.png',
                        help='Output image file name (default: hap_summary_plot.png)')

    args = parser.parse_args()
    
    # 校验输入数量是否对齐
    num_files = len(args.inputs)
    if len(args.sample_ids) != num_files or len(args.tags) != num_files:
        parser.error(f"Error: The number of --inputs ({num_files}), --sample-ids ({len(args.sample_ids)}), "
                     f"and --tags ({len(args.tags)}) must be exactly the same.")
        
    return args

def main():
    args = parse_args()
    
    all_data = []
    
    # 1. 循环读取和解析所有的 CSV 文件
    for file_path, sample_id, tag in zip(args.inputs, args.sample_ids, args.tags):
        if not os.path.exists(file_path):
            print(f"Warning: File {file_path} not found. Skipping...", file=sys.stderr)
            continue
            
        try:
            df = pd.read_csv(file_path)
            
            # 2. 根据用户指定的 Type 和 Filter 进行数据筛选
            filtered_df = df[(df['Type'] == args.type) & (df['Filter'] == args.filter)]
            
            if filtered_df.empty:
                print(f"Warning: No data found for Type={args.type}, Filter={args.filter} in {file_path}", file=sys.stderr)
                continue
                
            # 提取需要的指标
            # 考虑到 hap.py 的列名大小写，这里提取示例中的 METRIC.Recall, METRIC.Precision, METRIC.F1_Score
            row = filtered_df.iloc[0]
            all_data.append({
                'Sample_ID': sample_id,
                'Tag': tag,
                'Recall': float(row['METRIC.Recall']),
                'Precision': float(row['METRIC.Precision']),
                'F1_Score': float(row['METRIC.F1_Score'])
            })
        except Exception as e:
            print(f"Error processing {file_path}: {e}", file=sys.stderr)

    if not all_data:
        print("Error: No valid data to plot. Exiting.")
        sys.exit(1)
        
    plot_df = pd.DataFrame(all_data)
    print("\n--- Extracted Data for Plotting ---")
    print(plot_df.to_string(index=False))
    print("-----------------------------------\n")

    # 3. 开始绘图
    # 设置 Seaborn 风格，使图表更美观
    sns.set_theme(style="whitegrid")
    
    # 创建包含两个子图的画布 (左边: Recall vs Precision, 右边: F1 Score 柱状对比图)
    # 因为散点图只能展示两个维度，这里将 F1-score 作为点的大小(size) 或 独立画个图更直观。
    # 这里我们采用：
    # 轴 X=Recall, Y=Precision，点的颜色(hue)=Sample_ID, 点的形状(style)=Tag, 点的大小(size)=F1_Score
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 动态调整点的大小范围
    scatter = sns.scatterplot(
        data=plot_df,
        x='Recall',
        y='Precision',
        hue='Sample_ID',
        style='Tag',
        size='F1_Score',
        sizes=(100, 300), # 限制点的大小在 100 到 300 之间
        palette='Set1',
        ax=ax
    )
    
    # 优化图表细节
    ax.set_title(f"Hap.py Benchmark Result ({args.type} - {args.filter})", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('Recall', fontsize=12)
    ax.set_ylabel('Precision', fontsize=12)
    
    # 让图表四周留出一点 padding，方便观察边缘的点
    x_margin = (plot_df['Recall'].max() - plot_df['Recall'].min()) * 0.2 if len(plot_df) > 1 else 0.02
    y_margin = (plot_df['Precision'].max() - plot_df['Precision'].min()) * 0.2 if len(plot_df) > 1 else 0.02
    
    ax.set_xlim(plot_df['Recall'].min() - max(x_margin, 0.01), plot_df['Recall'].max() + max(x_margin, 0.01))
    ax.set_ylim(plot_df['Precision'].min() - max(y_margin, 0.01), plot_df['Precision'].max() + max(y_margin, 0.01))

    # 在每个点旁边隐约标注一下 F1-Score 的值，方便直接读取
    for i, row in plot_df.iterrows():
        ax.text(
            row['Recall'], 
            row['Precision'] + (max(y_margin, 0.01) * 0.05), 
            f"F1:{row['F1_Score']:.4f}", 
            fontsize=9, 
            ha='center'
        )

    # 把 Legend 放到图表外面，防止遮挡数据点
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
    
    plt.tight_layout()
    
    # 4. 保存图片
    plt.savefig(args.output, dpi=300)
    print(f"Success: Plot saved to '{args.output}'")

if __name__ == '__main__':
    main()