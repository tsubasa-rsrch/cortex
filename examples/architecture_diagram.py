#!/usr/bin/env python3
"""Generate architecture diagram for Cosmos Cookoff demo video."""

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import FancyArrowPatch
except ImportError:
    print("matplotlib not installed, install with: pip install matplotlib")
    raise

def create_architecture_diagram():
    """Create the Cortex + Cosmos + ReachyMini architecture diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(16, 10))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Title
    ax.text(8, 9.5, 'Cortex + Cosmos Reason2: Egocentric Social Reasoning',
            fontsize=18, fontweight='bold', ha='center', va='center',
            color='#1a1a2e')
    ax.text(8, 9.0, '"The camera view IS my view"',
            fontsize=12, fontstyle='italic', ha='center', va='center',
            color='#666666')

    # Colors
    cam_color = '#4ecdc4'
    cortex_color = '#45b7d1'
    cosmos_color = '#96ceb4'
    reachy_color = '#ffeaa7'
    filter_color = '#ff6b6b'

    # Camera box
    cam = patches.FancyBboxPatch((0.5, 6.5), 3, 1.5,
                                  boxstyle="round,pad=0.1",
                                  facecolor=cam_color, edgecolor='#2d3436',
                                  linewidth=2)
    ax.add_patch(cam)
    ax.text(2, 7.5, 'CAMERAS', fontsize=14, fontweight='bold',
            ha='center', va='center')
    ax.text(2, 7.0, 'Tapo C230/C260\n+ ReachyMini Camera', fontsize=9,
            ha='center', va='center')

    # Cortex Perception box
    cortex = patches.FancyBboxPatch((5, 5.5), 6, 3,
                                     boxstyle="round,pad=0.1",
                                     facecolor=cortex_color, edgecolor='#2d3436',
                                     linewidth=2, alpha=0.3)
    ax.add_patch(cortex)
    ax.text(8, 8.2, 'CORTEX Perception Layer', fontsize=14,
            fontweight='bold', ha='center', va='center')

    # Sub-modules inside Cortex
    modules = [
        (5.5, 7.0, 2.2, 0.8, 'Habituation\nFilter', '#74b9ff'),
        (8.3, 7.0, 2.2, 0.8, 'Orienting\nResponse', '#a29bfe'),
        (5.5, 5.8, 2.2, 0.8, 'Circadian\nRhythm', '#fd79a8'),
        (8.3, 5.8, 2.2, 0.8, 'Decision\nEngine', '#00cec9'),
    ]
    for x, y, w, h, label, color in modules:
        mod = patches.FancyBboxPatch((x, y), w, h,
                                      boxstyle="round,pad=0.05",
                                      facecolor=color, edgecolor='#2d3436',
                                      linewidth=1, alpha=0.7)
        ax.add_patch(mod)
        ax.text(x + w/2, y + h/2, label, fontsize=8,
                ha='center', va='center', fontweight='bold')

    # Filter stats
    ax.text(12.5, 7.5, '92% filtered', fontsize=11, fontweight='bold',
            ha='center', va='center', color=filter_color)
    ax.text(12.5, 7.0, '3,000+ events\nprocessed', fontsize=9,
            ha='center', va='center', color='#636e72')

    # Cosmos Reason2 box
    cosmos = patches.FancyBboxPatch((5, 2.5), 6, 2.5,
                                     boxstyle="round,pad=0.1",
                                     facecolor=cosmos_color, edgecolor='#2d3436',
                                     linewidth=2)
    ax.add_patch(cosmos)
    ax.text(8, 4.5, 'COSMOS REASON2 (Egocentric VLM)', fontsize=13,
            fontweight='bold', ha='center', va='center')
    ax.text(8, 3.8, 'Qwen3-VL-2B | 2.3s inference | Local (llama.cpp)',
            fontsize=10, ha='center', va='center')
    ax.text(8, 3.2, '"I see a person approaching me.\nThey want to interact."',
            fontsize=9, fontstyle='italic', ha='center', va='center',
            color='#2d3436')

    # ReachyMini box
    reachy = patches.FancyBboxPatch((5, 0.3), 6, 1.7,
                                     boxstyle="round,pad=0.1",
                                     facecolor=reachy_color, edgecolor='#2d3436',
                                     linewidth=2)
    ax.add_patch(reachy)
    ax.text(8, 1.5, 'REACHY MINI (Physical Response)', fontsize=13,
            fontweight='bold', ha='center', va='center')
    ax.text(8, 0.9, '88 emotions | 19 dances | Head tracking | Antennas',
            fontsize=10, ha='center', va='center')

    # Arrows
    arrow_style = dict(arrowstyle='->', color='#2d3436', lw=2.5,
                       connectionstyle='arc3,rad=0')

    # Camera → Cortex
    ax.annotate('', xy=(5, 7.25), xytext=(3.5, 7.25),
                arrowprops=arrow_style)
    ax.text(4.25, 7.6, 'RTSP\nFrames', fontsize=8, ha='center', va='center',
            color='#636e72')

    # Cortex → Cosmos
    ax.annotate('', xy=(8, 5.0), xytext=(8, 5.5),
                arrowprops=dict(arrowstyle='->', color='#e17055', lw=2.5))
    ax.text(9.5, 5.25, '9% novel\nevents', fontsize=9, ha='center',
            va='center', color='#e17055', fontweight='bold')

    # Cosmos → ReachyMini
    ax.annotate('', xy=(8, 2.0), xytext=(8, 2.5),
                arrowprops=dict(arrowstyle='->', color='#6c5ce7', lw=2.5))
    ax.text(9.8, 2.25, 'Action:\nengage/observe', fontsize=9,
            ha='center', va='center', color='#6c5ce7')

    # Side labels
    ax.text(14.5, 4.0, 'Fully Local\nNo Cloud API\nMIT License',
            fontsize=11, ha='center', va='center',
            fontweight='bold', color='#00b894',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#dfe6e9',
                      edgecolor='#00b894', linewidth=2))

    ax.text(14.5, 1.5, 'Team 668\ntsubasa-rsrch/cortex\n201 tests | 8,773 LOC',
            fontsize=9, ha='center', va='center', color='#636e72',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#ffeaa7',
                      edgecolor='#fdcb6e', linewidth=1))

    plt.tight_layout()
    output_path = '/Users/tsubasa/Documents/TsubasaWorkspace/cortex/examples/architecture_diagram.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"Saved to {output_path}")
    return output_path


if __name__ == '__main__':
    path = create_architecture_diagram()
    print(f"Architecture diagram: {path}")
