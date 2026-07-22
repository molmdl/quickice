Actual cost is lower with the synthetic coding plan
Large dataset detected (1983 sessions). This may take a while...
┌────────────────────────────────────────────────────────┐
│                       OVERVIEW                         │
├────────────────────────────────────────────────────────┤
│Sessions                                          1,983 │
│Messages                                         61,094 │
│Days                                                119 │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                    COST & TOKENS                       │
├────────────────────────────────────────────────────────┤
│Total Cost                                     $3086.46 │
│Avg Cost/Day                                     $25.94 │
│Avg Tokens/Session                                 1.8M │
│Median Tokens/Session                              1.2M │
│Input                                            393.7M │
│Output                                            26.3M │
│Cache Read                                      3209.8M │
│Cache Write                                        6.5M │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                      MODEL USAGE                       │
├────────────────────────────────────────────────────────┤
│ synthetic/hf:zai-org/GLM-5.1                           │
│  Messages                                       15,821 │
│  Input Tokens                                    51.0M │
│  Output Tokens                                    6.6M │
│  Cache Read                                    1036.8M │
│  Cache Write                                         0 │
│  Cost                                       $1107.6439 │
├────────────────────────────────────────────────────────┤
│ openrouter/z-ai/glm-5                                  │
│  Messages                                       12,689 │
│  Input Tokens                                   197.0M │
│  Output Tokens                                    6.5M │
│  Cache Read                                     488.9M │
│  Cache Write                                         0 │
│  Cost                                        $315.4364 │
├────────────────────────────────────────────────────────┤
│ synthetic/hf:zai-org/GLM-5                             │
│  Messages                                       10,133 │
│  Input Tokens                                    29.1M │
│  Output Tokens                                    4.4M │
│  Cache Read                                     529.5M │
│  Cache Write                                         0 │
│  Cost                                        $571.9035 │
├────────────────────────────────────────────────────────┤
│ opencode/big-pickle                                    │
│  Messages                                        7,690 │
│  Input Tokens                                    37.6M │
│  Output Tokens                                    2.8M │
│  Cache Read                                     345.7M │
│  Cache Write                                      6.5M │
│  Cost                                          $0.0000 │
├────────────────────────────────────────────────────────┤
│ synthetic/hf:zai-org/GLM-5.2                           │
│  Messages                                        7,554 │
│  Input Tokens                                    43.9M │
│  Output Tokens                                    6.3M │
│  Cache Read                                     686.5M │
│  Cache Write                                         0 │
│  Cost                                       $1050.2441 │
├────────────────────────────────────────────────────────┤
│ openrouter/minimax/minimax-m2.5                        │
│  Messages                                        2,291 │
│  Input Tokens                                    23.2M │
│  Output Tokens                                    1.1M │
│  Cache Read                                      60.1M │
│  Cache Write                                         0 │
│  Cost                                         $10.0363 │
├────────────────────────────────────────────────────────┤
│ openrouter/z-ai/glm-5.1                                │
│  Messages                                          984 │
│  Input Tokens                                     9.9M │
│  Output Tokens                                  533.0K │
│  Cache Read                                      46.6M │
│  Cache Write                                         0 │
│  Cost                                         $28.2611 │
├────────────────────────────────────────────────────────┤
│ opencode/minimax-m2.5-free                             │
│  Messages                                          221 │
│  Input Tokens                                   639.5K │
│  Output Tokens                                   89.5K │
│  Cache Read                                       6.6M │
│  Cache Write                                         0 │
│  Cost                                          $0.0000 │
├────────────────────────────────────────────────────────┤
│ synthetic/hf:MiniMaxAI/MiniMax-M2.5                    │
│  Messages                                          128 │
│  Input Tokens                                   277.3K │
│  Output Tokens                                   30.8K │
│  Cache Read                                       3.1M │
│  Cache Write                                         0 │
│  Cost                                          $2.1366 │
├────────────────────────────────────────────────────────┤
│ synthetic/hf:nvidia/Kimi-K2.5-NVFP4                    │
│  Messages                                           68 │
│  Input Tokens                                   580.2K │
│  Output Tokens                                   47.5K │
│  Cache Read                                       3.4M │
│  Cache Write                                         0 │
│  Cost                                          $0.4232 │
├────────────────────────────────────────────────────────┤
│ openrouter/minimax/minimax-m2.7                        │
│  Messages                                           44 │
│  Input Tokens                                   520.7K │
│  Output Tokens                                   54.5K │
│  Cache Read                                       2.5M │
│  Cache Write                                         0 │
│  Cost                                          $0.3739 │
├────────────────────────────────────────────────────────┤
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                      TOOL USAGE                        │
├────────────────────────────────────────────────────────┤
│ bash               ████████████████████ 34059 (42.5%)  │
│ read               █████████████        23026 (28.7%)  │
│ edit               █████                9182 (11.4%)   │
│ grep               ██                   4509 ( 5.6%)   │
│ glob               █                    2891 ( 3.6%)   │
│ write              █                    2631 ( 3.3%)   │
│ task               █                    1688 ( 2.1%)   │
│ webfetch           █                    998 ( 1.2%)    │
│ question           █                    793 ( 1.0%)    │
│ todowrite          █                    303 ( 0.4%)    │
│ invalid            █                    118 ( 0.1%)    │
│ websearch          █                     15 ( 0.0%)    │
│ codesearch         █                      5 ( 0.0%)    │
│ skill              █                      1 ( 0.0%)    │
└────────────────────────────────────────────────────────┘

