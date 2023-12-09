from utils.utils import VAR_TYPE, VALUE_TYPE, QUANTIZED_VALUE
from transformers.data.data_collator import tolist

def process_quantized_value(args, tokenizer, examples):
    entry_key = "entry_variables"
    src_key = "src_seq"
    var_type_key = "var_type_seq"
    value_type_key = "value_type_seq"
    abstract_value_key = "abstract_value_seq"

    # remove the samples with empty all ## labels
    entry_variables = []
    src_seq = []
    var_type_seq = []
    value_type_seq = []
    abstract_value_seq = []
    total = len(examples[src_key])
    for i in range(total):
        var_types_labels_i = examples[var_type_key][i].split()
        value_types_labels_i = examples[value_type_key][i].split()
        abstract_values_labels_i = examples[abstract_value_key][i].split()
        if len(set(var_types_labels_i)) == 1 or len(set(value_types_labels_i)) == 1 or len(set(abstract_values_labels_i)) == 1:
            continue
        else:
            entry_variables.append(examples[entry_key][i])
            src_seq.append(examples[src_key][i])
            var_type_seq.append(examples[var_type_key][i])
            value_type_seq.append(examples[value_type_key][i])
            abstract_value_seq.append(examples[abstract_value_key][i])

    total = len(src_seq)
    tokenized_src = tokenizer(src_seq)
    var_type_labels = []
    value_type_labels = []
    abstract_value_labels = []
    for i in range(total):
        var_type_lb = []
        value_type_lb = []
        abstract_value_lb = []

        var_types_labels_i = var_type_seq[i].split()
        value_types_labels_i = value_type_seq[i].split()
        abstract_values_labels_i = abstract_value_seq[i].split()

        vva_idx = 0
        for id in tolist(tokenized_src['input_ids'][i]):
            if id == tokenizer.pad_token_id or id == tokenizer.sep_token_id or id == tokenizer.cls_token_id or id == tokenizer.unk_token_id:
                var_type_lb.append(-100)
                value_type_lb.append(-100)
                abstract_value_lb.append(-100)
            else:
                token = tokenizer._convert_id_to_token(id)
                if token.startswith("Ġ"): # This implementation is specifically for RoBerTa Tokenizer
                    vva_idx += 1
                if var_types_labels_i[vva_idx] == "##":
                    var_type_lb.append(-100)
                else:
                    var_type_lb.append(VAR_TYPE[var_types_labels_i[vva_idx]])
                if value_types_labels_i[vva_idx] == "##":
                    value_type_lb.append(-100)
                else:
                    value_type_lb.append(VALUE_TYPE[value_types_labels_i[vva_idx]])
                if abstract_values_labels_i[vva_idx] == "##":
                    abstract_value_lb.append(-100)
                else:
                    abstract_value_lb.append(QUANTIZED_VALUE[abstract_values_labels_i[vva_idx]])
        assert len(var_type_lb) == len(value_type_lb) == len(abstract_value_lb) == len(tokenized_src['input_ids'][i]), f"No. {i} sample has different length between labels and input_ids before prepending entry variables."

        var_type_labels.append(var_type_lb)
        value_type_labels.append(value_type_lb)
        abstract_value_labels.append(abstract_value_lb)

    tokenized_entry = tokenizer(entry_variables, truncation=True, max_length=args.max_input_value_length)
    assert len(tokenized_entry["input_ids"]) == total, f"Entry variables and source code have different length."
    #prepend entry variables to src_seq, and add -100 to all labels
    tokenized_src_with_inputs = {"input_ids": [], "attention_mask": []}
    for i in range(total):
        tokenized_src_with_inputs["input_ids"].append(tokenized_entry["input_ids"][i] + tokenized_src["input_ids"][i])
        tokenized_src_with_inputs["attention_mask"].append(tokenized_entry["attention_mask"][i] + tokenized_src["attention_mask"][i])
        var_type_labels[i] = [-100 for i in range(len(tokenized_entry["input_ids"][i]))] + var_type_labels[i]
        value_type_labels[i] = [-100 for i in range(len(tokenized_entry["input_ids"][i]))] + value_type_labels[i]
        abstract_value_labels[i] = [-100 for i in range(len(tokenized_entry["input_ids"][i]))] + abstract_value_labels[i]

    assert len(var_type_lb) == len(value_type_lb) == len(abstract_value_lb) == len(tokenized_src['input_ids'][i]), f"No. {i} sample has different length between labels and input_ids after prepending entry variables."

    block_size = args.max_seq_length

    # group samples with the maximum length of block_size
    features = {"input_ids": [], "attention_mask": [], "var_type_labels": [], "value_type_labels": [], "abstract_value_labels": []}
    src_buffer = []
    attn_masks_buffer = []
    var_type_buffer = []
    value_type_buffer = []
    abstract_value_buffer = []
    for idx, src in enumerate(tokenized_src_with_inputs["input_ids"]):
        # We will try to truncate the samples as few as possible while concatenating them
        if len(src_buffer) + len(src) > block_size:
            features["input_ids"].append(src_buffer[:block_size])
            src_buffer = []
            features["attention_mask"].append(attn_masks_buffer[:block_size])
            attn_masks_buffer = []
            features["var_type_labels"].append(var_type_buffer[:block_size])
            var_type_buffer = []
            features["value_type_labels"].append(value_type_buffer[:block_size])
            value_type_buffer = []
            features["abstract_value_labels"].append(abstract_value_buffer[:block_size])
            abstract_value_buffer = []
        src_buffer += src
        attn_masks_buffer += tokenized_src_with_inputs["attention_mask"][idx]
        var_type_buffer += var_type_labels[idx]
        value_type_buffer += value_type_labels[idx]
        abstract_value_buffer += abstract_value_labels[idx]
    # add the last sample
    features["input_ids"].append(src_buffer[:block_size])
    features["attention_mask"].append(attn_masks_buffer[:block_size])
    features["var_type_labels"].append(var_type_buffer[:block_size])
    features["value_type_labels"].append(value_type_buffer[:block_size])
    features["abstract_value_labels"].append(abstract_value_buffer[:block_size])

    return features
