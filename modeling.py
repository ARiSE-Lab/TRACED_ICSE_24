import torch
import torch.nn as nn
from transformers import RobertaModel, RobertaPreTrainedModel
from transformers.models.roberta.modeling_roberta import RobertaPooler
from transformers.models.roberta.modeling_roberta import RobertaForMaskedLM
from transformers.file_utils import add_start_docstrings
from transformers.modeling_outputs import TokenClassifierOutput
from transformers.modeling_outputs import MaskedLMOutput
from torch.nn import CrossEntropyLoss
from typing import List, Optional, Tuple, Union

@add_start_docstrings("""TRACED Model for comprehensive code understanding with MLM, VarType, ValueType, and AbsValue predictions""")
class TracedModel(RobertaForMaskedLM):
    def __init__(self, config, w_mlm=1.0, w_var_type=1.0, w_value_type=1.0, w_abs_value=1.0, num_var_type=3, num_value_type=6, num_abs_value=11):
        super().__init__(config)
        self.w_mlm = w_mlm
        self.w_var_type = w_var_type
        self.w_value_type = w_value_type
        self.w_abs_value = w_abs_value
        self.num_var_type = num_var_type
        self.num_value_type = num_value_type
        self.num_abs_value = num_abs_value
        classifier_dropout = (
            config.classifier_dropout if config.classifier_dropout is not None else config.hidden_dropout_prob
        )
        self.dropout = nn.Dropout(classifier_dropout)
        self.var_type_cls = nn.Linear(config.hidden_size, self.num_var_type)
        self.value_type_cls = nn.Linear(config.hidden_size, self.num_value_type)
        self.abs_value_cls = nn.Linear(config.hidden_size, self.num_abs_value)

        # Initialize weights and apply final processing
        self.post_init()

    def forward(
        self,
        input_ids: Optional[torch.LongTensor] = None,
        attention_mask: Optional[torch.FloatTensor] = None,
        token_type_ids: Optional[torch.LongTensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        head_mask: Optional[torch.FloatTensor] = None,
        inputs_embeds: Optional[torch.FloatTensor] = None,
        mlm_labels: Optional[torch.LongTensor] = None,
        var_type_labels: Optional[torch.LongTensor] = None,
        value_type_labels: Optional[torch.LongTensor] = None,
        abs_value_labels: Optional[torch.LongTensor] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
    ) -> Union[Tuple[torch.Tensor], MaskedLMOutput]:

        outputs = self.roberta(
            input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )

        sequence_output = outputs[0]
        
        # MLM prediction
        lm_prediction_scores = self.lm_head(sequence_output)
        masked_lm_loss = None
        if mlm_labels is not None:
            loss_fct = CrossEntropyLoss()
            masked_lm_loss = loss_fct(lm_prediction_scores.view(-1, self.config.vocab_size), mlm_labels.view(-1))

        # VarType, ValueType, AbsValue prediction
        sequence_output = self.dropout(sequence_output)
        var_type_logits = self.var_type_cls(sequence_output)
        var_type_loss = None
        if var_type_labels is not None:
            loss_fct = CrossEntropyLoss()
            var_type_loss = loss_fct(var_type_logits.view(-1, self.num_var_type), var_type_labels.view(-1))

        value_type_logits = self.value_type_cls(sequence_output)
        value_type_loss = None
        if value_type_labels is not None:
            loss_fct = CrossEntropyLoss()
            value_type_loss = loss_fct(value_type_logits.view(-1, self.num_value_type), value_type_labels.view(-1))

        abs_value_logits = self.abs_value_cls(sequence_output)
        abs_value_loss = None
        if abs_value_labels is not None:
            loss_fct = CrossEntropyLoss()
            abs_value_loss = loss_fct(abs_value_logits.view(-1, self.num_abs_value), abs_value_labels.view(-1))

        loss = self.w_mlm * masked_lm_loss + self.w_var_type * var_type_loss + self.w_value_type * value_type_loss + self.w_abs_value * abs_value_loss
                
        output = (lm_prediction_scores, var_type_logits, value_type_logits, abs_value_logits) + outputs[2:]
        return ((loss, masked_lm_loss, var_type_loss, value_type_loss, abs_value_loss) + output) if masked_lm_loss is not None else output


@add_start_docstrings("""TRACED Model for code coverage prediction.""")
class TracedModelForCoverage(RobertaPreTrainedModel):
    _keys_to_ignore_on_load_missing = [r"position_ids"]

    def __init__(self, config):
        super().__init__(config)
        self.num_labels = 2
        self.roberta = RobertaModel(config, add_pooling_layer=False)
        classifier_dropout = (
            config.classifier_dropout if config.classifier_dropout is not None else config.hidden_dropout_prob
        )
        self.dropout = nn.Dropout(classifier_dropout)
        self.classifier = nn.Linear(config.hidden_size, self.num_labels)

        # Initialize weights and apply final processing
        self.post_init()

    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        token_type_ids=None,
        position_ids=None,
        head_mask=None,
        inputs_embeds=None,
        labels=None,
        output_attentions=None,
        output_hidden_states=None,
        return_dict=None,
    ):
        r"""
        labels (`torch.LongTensor` of shape `(batch_size, sequence_length)`, *optional*):
            Labels for computing the token classification loss. Indices should be in `[0, ..., config.num_labels - 1]`.
        """
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        outputs = self.roberta(
            input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )

        sequence_output = outputs[0]

        sequence_output = self.dropout(sequence_output)
        logits = self.classifier(sequence_output)

        loss = None
        if labels is not None:
            loss_fct = CrossEntropyLoss()
            # Only keep active parts of the loss
            if attention_mask is not None:
                active_loss = attention_mask.view(-1) == 1
                active_logits = logits.view(-1, self.num_labels)
                active_labels = torch.where(
                    active_loss, labels.view(-1), torch.tensor(loss_fct.ignore_index).type_as(labels)
                )
                loss = loss_fct(active_logits, active_labels)
            else:
                loss = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))

        if not return_dict:
            output = (logits,) + outputs[2:]
            return ((loss,) + output) if loss is not None else output

        return TokenClassifierOutput(
            loss=loss,
            logits=logits,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )
    

@add_start_docstrings("""TRACED Model for encoding source code as representation.""")
class TracedForEncoder(RobertaPreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.roberta = RobertaModel(config, add_pooling_layer=True)
        self.init_weights()

    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        token_type_ids=None,
        position_ids=None,
        head_mask=None,
        inputs_embeds=None,
        output_attentions=None,
        output_hidden_states=None,
        **kwargs
    ):
        assert kwargs == {}, f"Unexpected keyword arguments: {list(kwargs.keys())}."
        assert attention_mask is not None
        outputs = self.roberta(
            input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
        )

        sequence_output, pooled_output = outputs[:2]  # token rep (bs * num_sent, seq_len, hidden), [CLS] rep (bs * num_sent, hidden)

        return pooled_output

@add_start_docstrings("""TRACED Model for classification tasks""")
class TracedForCls(RobertaPreTrainedModel):
    def __init__(self, config, new_pooler):
        super().__init__(config)
        self.roberta = RobertaModel(config, add_pooling_layer=True)
        self.pooler = RobertaPooler(config) if new_pooler else None
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        self.output_proj = nn.Linear(config.hidden_size, 2)
        self.init_weights()
    
    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        token_type_ids=None,
        position_ids=None,
        head_mask=None,
        inputs_embeds=None,
        labels=None,
        output_attentions=None,
        output_hidden_states=None,
    ):
        assert attention_mask is not None
        outputs = self.roberta(
            input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
        )

        if self.pooler is not None:
            pooled_output = self.pooler(outputs[0])
        else:
            pooled_output = outputs[1]

        pooled_output = self.dropout(pooled_output)
        logits = self.output_proj(pooled_output)
        outputs = (logits,)

        assert labels is not None

        loss_fct = CrossEntropyLoss()
        cls_loss = loss_fct(logits.view(-1, 2), labels.view(-1))
        outputs = (cls_loss,) + outputs

        return outputs

@add_start_docstrings("""TRACED Model for runtime value prediction.""")
class TracedForValue(RobertaForMaskedLM):
    def __init__(self, config, num_value):
        super().__init__(config)
        self.num_value = num_value
        classifier_dropout = (
            config.classifier_dropout if config.classifier_dropout is not None else config.hidden_dropout_prob
        )
        self.dropout = nn.Dropout(classifier_dropout)
        self.value_cls = nn.Linear(config.hidden_size, self.num_value)

        # Initialize weights and apply final processing
        self.post_init()

    def forward(
        self,
        input_ids: Optional[torch.LongTensor] = None,
        attention_mask: Optional[torch.FloatTensor] = None,
        token_type_ids: Optional[torch.LongTensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        head_mask: Optional[torch.FloatTensor] = None,
        inputs_embeds: Optional[torch.FloatTensor] = None,
        value_labels: Optional[torch.LongTensor] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
    ) -> Union[Tuple[torch.Tensor], MaskedLMOutput]:
        r"""
        labels (`torch.LongTensor` of shape `(batch_size, sequence_length)`, *optional*):
            Labels for computing the token classification loss. Indices should be in `[0, ..., config.num_labels - 1]`.
        """
        outputs = self.roberta(
            input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )

        sequence_output = outputs[0]

        value_logits = self.value_cls(sequence_output)
        loss_fct = CrossEntropyLoss()
        loss = loss_fct(value_logits.view(-1, self.num_value), value_labels.view(-1))
        output = (value_logits,) + outputs[2:]
        return ((loss,) + output)
