from transformers.data.data_collator import DataCollatorForLanguageModeling, _torch_collate_batch
from typing import Any, Dict, List, Union

class DataCollatorForTraced(DataCollatorForLanguageModeling):
    def torch_call(self, examples: List[Union[List[int], Any, Dict[str, Any]]]) -> Dict[str, Any]:
        # Handle dict or lists with proper padding and conversion to tensor.
        input_ids = [example["input_ids"] for example in examples]
        attention_mask = [example["attention_mask"] for example in examples]
        var_type_labels = [example["var_type_labels"] for example in examples]
        value_type_labels = [example["value_type_labels"] for example in examples]
        abs_value_labels = [example["abstract_value_labels"] for example in examples]
        batch = {}
        batch["input_ids"] = _torch_collate_batch(input_ids, self.tokenizer, pad_to_multiple_of=self.pad_to_multiple_of)
        batch["attention_mask"] = _torch_collate_batch(attention_mask, self.tokenizer, pad_to_multiple_of=self.pad_to_multiple_of)
        batch["var_type_labels"] = _torch_collate_batch(var_type_labels, self.tokenizer, pad_to_multiple_of=self.pad_to_multiple_of)
        batch["value_type_labels"] = _torch_collate_batch(value_type_labels, self.tokenizer, pad_to_multiple_of=self.pad_to_multiple_of)
        batch["abs_value_labels"] = _torch_collate_batch(abs_value_labels, self.tokenizer, pad_to_multiple_of=self.pad_to_multiple_of)
        

        # If special token mask has been preprocessed, pop it from the dict.
        special_tokens_mask = batch.pop("special_tokens_mask", None)
        batch["input_ids"], batch["mlm_labels"] = self.torch_mask_tokens(
            batch["input_ids"], special_tokens_mask=special_tokens_mask
        )

        return batch
    
    def torch_call(self, examples: List[Union[List[int], Any, Dict[str, Any]]]) -> Dict[str, Any]:
        # Handle dict or lists with proper padding and conversion to tensor.
        input_ids = [example["input_ids"] for example in examples]
        attention_mask = [example["attention_mask"] for example in examples]
        var_type_labels = [example["var_type_labels"] for example in examples]
        value_type_labels = [example["value_type_labels"] for example in examples]
        abs_value_labels = [example["concrete_value_labels"] for example in examples]
        batch = {}
        batch["input_ids"] = _torch_collate_batch(input_ids, self.tokenizer, pad_to_multiple_of=self.pad_to_multiple_of)
        batch["attention_mask"] = _torch_collate_batch(attention_mask, self.tokenizer, pad_to_multiple_of=self.pad_to_multiple_of)
        batch["var_type_labels"] = _torch_collate_batch(var_type_labels, self.tokenizer, pad_to_multiple_of=self.pad_to_multiple_of)
        batch["value_type_labels"] = _torch_collate_batch(value_type_labels, self.tokenizer, pad_to_multiple_of=self.pad_to_multiple_of)
        batch["concrete_value_labels"] = _torch_collate_batch(abs_value_labels, self.tokenizer, pad_to_multiple_of=self.pad_to_multiple_of)
        

        # If special token mask has been preprocessed, pop it from the dict.
        special_tokens_mask = batch.pop("special_tokens_mask", None)
        batch["input_ids"], batch["mlm_labels"] = self.torch_mask_tokens(
            batch["input_ids"], special_tokens_mask=special_tokens_mask
        )

        return batch