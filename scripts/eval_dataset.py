from utils import shuffle_lists, calculate_correlation, load_newsroom, load_summEval, calculate_uncertainty, load_sf_data, CompareResultObject, insert_index_to_anchors
import random
from sorting import merge_sort_indices
import numpy as np
from tqdm import tqdm
import json



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, default='SumEval')
    parser.add_argument('--save_path', type=str, default='./results.jsonl')
    parser.add_argument('--aspect', type=str, default='coherence')
    parser.add_argument('--eval_method', type=str, default='pairwise comparison')
    parser.add_argument('--scaling_anchor_size', type=int, default=0)
    parser.add_argument('--eval_size', type=int, default=300)
    parser.add_argument('--engine', type=str, default='mistralai/Mistral-7B-Instruct-v0.1')
    parser.add_argument('--confidence_beam', action="store_true")
    parser.add_argument('--prob_gap', type=float, default=0.15)
    parser.add_argument('--beam_size', type=int, default=100)
    parser.add_argument('--with_input', action="store_true")
    parser.add_argument('--calibration', action="store_true")
    args = parser.parse_args()

    print('aspect:', args.aspect)
    print('engine:', args.engine)
    print('dataset:', args.dataset)
    print('confidence_beam:', args.confidence_beam)
    print('beam_size:', args.beam_size)
    print('calibration:', args.calibration)

    params = {
        'dataset': args.dataset,
        'engine': args.engine,
        'aspect': args.aspect,
        'eval_method': args.eval_method,
        'confidence_beam': args.confidence_beam,
        'beam_size': args.beam_size,
        'api_call': 0,
        'prob_gap': args.prob_gap,
        'with_input': args.with_input,
        'compare_log': {},
        'calibration': args.calibration,
    }
    # Load the dataset
    if args.dataset == 'SumEval':
        summ_eval_path = 'data/SummEval/model_annotations.aligned.paired.jsonl'
        input_doc, output_doc, scores_doc = load_summEval(summ_eval_path, flat_output=False)
    elif args.dataset == 'newsroom':
        newsroom_path = 'data/newsroom/newsroom.json'
        input_doc, output_doc, scores_doc = load_newsroom(newsroom_path, flat_output=False)
    else:
        print('Dataset not supported.')
        assert False

    scores_doc = scores_doc[args.aspect]
    ranking_indices_list = []
    scores_list = []
    progress_bar = tqdm(total=len(input_doc), desc='Processing')
    base_idx_cnt = 0
    spearman_corr_list, kendall_tau_list = [], []
    for input, output, scores in zip(input_doc, output_doc, scores_doc):
        input, output, scores = shuffle_lists(input, output, scores)
        ranking_indices = merge_sort_indices(input, output, params)
        ranking_indices_list.append([idx+base_idx_cnt for idx in ranking_indices])
        scores_list.append(scores)
        base_idx_cnt += len(input)
        progress_bar.update(1)
        print(np.array(scores)[ranking_indices])
        spearman_corr, kendall_tau, mae = calculate_correlation(np.array(scores)[ranking_indices], list(range(len(scores))))
        spearman_corr_list.append(spearman_corr)
        kendall_tau_list.append(kendall_tau)
        print('api_call:', params['api_call'])
        params['api_call'] = 0


    ranking_indices_flatten = np.array(ranking_indices_list).T.flatten().tolist()
    scores_flatten = np.array(scores_list).flatten()
    # Save the results if needed
    results = {
        'aspect': args.aspect,
        'confidence_beam': args.confidence_beam,
        'beam_size': params['beam_size'],
        'engine': args.engine,
        'dataset': args.dataset,
        'human_scores': scores_flatten.tolist(),
        'gpt_ranking': ranking_indices_flatten,
        'compare_log': {str(key):val for key, val in params['compare_log'].items()},
        'spearmans:': np.average(spearman_corr_list).tolist(),
        'kendall_tau': np.average(kendall_tau_list).tolist(),
    }


    progress_bar.close()
    print('---------------------------------')
    print('spearmans:', np.mean(spearman_corr_list))
    print('kendall_tau:', np.mean(kendall_tau_list))
    print('aspect:', args.aspect)
    print('engine:', args.engine)
    print('dataset:', args.dataset)
    print('confidence_beam:', args.confidence_beam)
    print('beam_size:', params['beam_size'])
    print('calibration:', args.calibration)
