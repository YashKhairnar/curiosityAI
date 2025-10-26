import numpy as np
import vec2text
import torch
from chromadb import Documents, EmbeddingFunction, Embeddings
from transformers import AutoModel, AutoTokenizer

class Models:
        encoder = AutoModel.from_pretrained("sentence-transformers/gtr-t5-base").encoder.to("mps")
        tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/gtr-t5-base")
        corrector = vec2text.load_pretrained_corrector("gtr-base")
    

class MyEmbeddingFunction(EmbeddingFunction):
        def __call__(self, input: Documents) -> Embeddings:
            # Access outer class attributes using DB.attribute_name
            inputs = Models.tokenizer(
                input,
                return_tensors="pt",
                max_length=768,
                truncation=True,
                padding="max_length",
            ).to('mps')
            
            # Get embeddings from the model
            with torch.no_grad():
                model_output = Models.encoder(
                    input_ids=inputs['input_ids'],
                    attention_mask=inputs['attention_mask']
                )
                hidden_state = model_output.last_hidden_state
            
            # Pool the embeddings
            embeddings = vec2text.models.model_utils.mean_pool(
                hidden_state,
                inputs['attention_mask']
            )
            
            # Convert to list format for ChromaDB
            return embeddings.cpu().detach().numpy().tolist()


    