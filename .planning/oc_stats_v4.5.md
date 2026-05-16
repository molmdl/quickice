Actual cost is lower with as we use the synthetic coding plan instead of API pricing
Large dataset detected (1254 sessions). This may take a while...
┌────────────────────────────────────────────────────────┐
│                       OVERVIEW                         │
├────────────────────────────────────────────────────────┤
│Sessions                                          1,254 │
│Messages                                         36,363 │
│Days                                                 52 │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                    COST & TOKENS                       │
├────────────────────────────────────────────────────────┤
│Total Cost                                      $920.90 │
│Avg Cost/Day                                     $17.71 │
│Avg Tokens/Session                                 1.4M │
│Median Tokens/Session                            905.4K │
│Input                                            298.3M │
│Output                                            13.4M │
│Cache Read                                      1479.4M │
│Cache Write                                        6.5M │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                      MODEL USAGE                       │
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
│  Messages                                        9,986 │
│  Input Tokens                                    28.7M │
│  Output Tokens                                    4.4M │
│  Cache Read                                     522.4M │
│  Cache Write                                         0 │
│  Cost                                        $564.2313 │
├────────────────────────────────────────────────────────┤
│ opencode/big-pickle                                    │
│  Messages                                        7,690 │
│  Input Tokens                                    37.6M │
│  Output Tokens                                    2.8M │
│  Cache Read                                     345.7M │
│  Cache Write                                      6.5M │
│  Cost                                          $0.0000 │
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
│ bash               ████████████████████ 18781 (41.3%)  │
│ read               █████████████        12289 (27.0%)  │
│ edit               ██████               5957 (13.1%)   │
│ grep               ██                   2475 ( 5.4%)   │
│ glob               █                    1845 ( 4.1%)   │
│ write              █                    1711 ( 3.8%)   │
│ task               █                    1044 ( 2.3%)   │
│ question           █                    698 ( 1.5%)    │
│ webfetch           █                    498 ( 1.1%)    │
│ invalid            █                    107 ( 0.2%)    │
│ todowrite          █                     37 ( 0.1%)    │
│ websearch          █                     15 ( 0.0%)    │
│ codesearch         █                      5 ( 0.0%)    │
│ skill              █                      1 ( 0.0%)    │
└────────────────────────────────────────────────────────┘

