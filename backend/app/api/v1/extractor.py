from flask import request, jsonify
import torch
from app.api.v1 import bp
from app.utils.common import process_keywords
import anthropic
import os, numpy as np
from app.utils.chroma import get_chroma_collection
import umap, json, uuid
from hdbscan import HDBSCAN
import matplotlib.pyplot as plt
from sklearn.mixture import GaussianMixture  # For GMM
from scipy.optimize import minimize  # For inverse design optimization
import vec2text

client = anthropic.Anthropic(
    api_key=os.environ.get("CLAUDE_API_KEY")
)

SUMMARIZATION_PROMPT = '''
            Summarize this research abstract in exactly 20-25 words, preserving the core research question, methodology, and key finding. 
            Focus on what was studied, how, and the main result. Use active voice where possible, include the primary outcome/conclusion, 
            and avoid jargon unless essential.   
        '''
umap_3d = umap.UMAP(n_components=3, random_state=42) # for UI
reducer = umap.UMAP(n_components=10, random_state=42)  # Reduce to 10 dims for efficiency for clustering
clusterer = HDBSCAN(
    min_cluster_size=15,  # Min points for a cluster; increase for larger clusters
    min_samples=5,        # Controls noise sensitivity; higher = more outliers (gaps)
    metric='euclidean',   # Good for reduced_embeddings; use 'cosine' if normalized
    cluster_selection_method='eom'  # 'eom' for balanced clusters; 'leaf' for finer ones
)

corrector = vec2text.load_pretrained_corrector('gtr-base')

@bp.post("/extractor")
def extractor():
    """
    Accepts JSON and echoes it back with a server tag.
    No auth; allows any user.
    """
    collection  = get_chroma_collection()
    
    payload = request.get_json(silent=True) or {}
    keywords = payload.get('keywords', [])

    max_results = payload.get('max_results', 100) 

    records = process_keywords(keywords, max_results=max_results)
    l = len(records)
    
    #store in the chroma DB
    collection.add(
        ids = [uuid.uuid4().hex for _ in range(l)],
        documents= [ item['summary'] for item in records],
        metadatas= [ {'link':item['link'], 'title':item['title']} for item in records ]
    )

    return jsonify(
       message = 'records stored in the DB'
    ), 200


# @bp.get('/findIdeas')
# def findIdeas():
#     collection = get_chroma_collection()
#     results = collection.get(
#         include=['embeddings', 'metadatas']
#     )
#     ids = results['ids']
#     # emb = results['embeddings']
#     # reduced_embeddings = reducer.fit_transform(emb)
#     reduced_embeddings = results['embeddings']

#     # # Map IDs to reduced reduced_embeddings
#     # # id_to_reduced_emb = {
#     # #     id: reduced_embedding 
#     # #     for id, reduced_embedding in zip(ids, reduced_embeddings)
#     # # }

#     gmm = GaussianMixture(n_components=5, random_state=42)
#     gmm.fit(reduced_embeddings)     

#     # # Compute log-probabilities and convert to densities (exp for positive values)
#     log_probs_gmm = gmm.score_samples(reduced_embeddings)
#     densities_gmm = log_probs_gmm # np.exp( )
#     print(f"Log probabilities: min={log_probs_gmm.min():.2f}, "
#               f"mean={log_probs_gmm.mean():.2f}, max={log_probs_gmm.max():.2f}")
        
#     # Find gaps (bottom 10% = low density)
#     threshold_percentile = 10
#     log_threshold = np.percentile(log_probs_gmm, threshold_percentile)
#     gap_indices = np.where(log_probs_gmm < log_threshold)[0]
        
#     print(f"Found {len(gap_indices)} research gaps (bottom {threshold_percentile}%)")
#     # # Option 2: Inverse Design via Optimization
#     # # Start from a perturbed point (e.g., near a cluster but far semantically)
#     initial_v = reduced_embeddings.mean(axis=0) + np.random.normal(0, 0.5, reduced_embeddings.shape[1])

#     # # Define negative density function for minimization (low density = high -density)
#     def neg_density_gmm(x, gmm):
#         return -np.exp(gmm.score_samples(x.reshape(1, -1)))[0]
    
#     # # Bounds: Constrain to realistic norms (data min/max per dimension)
#     bounds = list(zip(reduced_embeddings.min(axis=0), reduced_embeddings.max(axis=0)))

#     # # Optimize to minimize density
#     result_gmm = minimize(neg_density_gmm, initial_v, args=(gmm,), bounds=bounds, method='L-BFGS-B')
#     v_gmm = result_gmm.x
#     # print("\nOptimized low-density v (GMM):", v_gmm)
#     # print("Density at v (GMM):", np.exp(gmm.score_samples(v_gmm.reshape(1, -1)))[0])

#     component_means = gmm.means_
#     midpoint = (component_means[0] + component_means[1]) / 2  # Between first two components
#     initial_v_adj = midpoint + np.random.normal(0, 0.2, reduced_embeddings.shape[1])

#     result_adj = minimize(neg_density_gmm, initial_v_adj, args=(gmm,), bounds=bounds, method='L-BFGS-B')
#     v_adj = result_adj.x
#     # print("\nSemantically adjacent low-density: ", v_adj)
#     # print("Density at adjacent v:", np.exp(gmm.score_samples(v_adj.reshape(1, -1)))[0])

#     # # CRITICAL: vec2text expects 2D array (batch_size, embedding_dim)
#     v_adj_2d = v_adj.reshape(1, -1).astype(np.float32)
        
#     # print(f"\nShape before inversion: {v_adj_2d.shape}")
#     # print(f"Type: {type(v_adj_2d)}")
        
#     # # Convert to torch tensor
#     v_adj_tensor = torch.tensor(v_adj_2d,device='mps')
        
#     # # Invert embedding to text
#     text = vec2text.invert_embeddings(
#             embeddings=v_adj_tensor,
#             corrector=corrector
#     )

#     return jsonify(
#         text = text
#     ),200

#     # collection.delete(ids=ids)


@bp.get('/findIdeas')
def findIdeas():
    try:
        collection = get_chroma_collection()
        results = collection.get(
            include=['embeddings', 'metadatas', 'documents']
        )
        
        ids = results['ids']
        embeddings = np.array(results['embeddings'], dtype=np.float32)
        documents = results['documents']
        metadatas = results['metadatas']
        
        print(f"Loaded {len(ids)} embeddings with shape {embeddings.shape}")
        
        # Verify dimension
        if embeddings.shape[1] != 768:
            return jsonify({
                'error': f'Expected 768-dim embeddings, got {embeddings.shape[1]}'
            }), 400
        
        # Fit GMM
        gmm = GaussianMixture(n_components=3, random_state=42)
        gmm.fit(embeddings)
        
        # Work in log space to avoid overflow
        log_probs = gmm.score_samples(embeddings)
        
        print(f"Log probabilities: min={log_probs.min():.2f}, "
              f"mean={log_probs.mean():.2f}, max={log_probs.max():.2f}")
        
        # Find gaps (bottom 10% = low density)
        threshold_percentile = 10
        log_threshold = np.percentile(log_probs, threshold_percentile)
        gap_indices = np.where(log_probs < log_threshold)[0]
        
        print(f"Found {len(gap_indices)} research gaps (bottom {threshold_percentile}%)")
        
        if len(gap_indices) == 0:
            return jsonify({
                'ok': False,
                'message': 'No gaps found'
            }), 200
        
        # Optimization: Find novel low-density point
        def neg_log_density(x, gmm):
            return -gmm.score_samples(x.reshape(1, -1))[0]
        
        bounds = list(zip(embeddings.min(axis=0), embeddings.max(axis=0)))
        
        # Strategy 1: Start from mean + noise
        initial_v = embeddings.mean(axis=0) + np.random.normal(0, 0.5, embeddings.shape[1])
        result_1 = minimize(neg_log_density, initial_v, args=(gmm,), bounds=bounds, method='L-BFGS-B')
        v_1 = result_1.x
        log_density_1 = gmm.score_samples(v_1.reshape(1, -1))[0]
        
        # Strategy 2: Start from midpoint between clusters
        component_means = gmm.means_
        midpoint = (component_means[0] + component_means[1]) / 2
        initial_v_2 = midpoint + np.random.normal(0, 0.2, embeddings.shape[1])
        result_2 = minimize(neg_log_density, initial_v_2, args=(gmm,), bounds=bounds, method='L-BFGS-B')
        v_2 = result_2.x
        log_density_2 = gmm.score_samples(v_2.reshape(1, -1))[0]
        
        print(f"Optimized gap 1: log_density={log_density_1:.2f}")
        print(f"Optimized gap 2: log_density={log_density_2:.2f}")
        
        # Choose the lower density one (bigger gap)
        if log_density_1 < log_density_2:
            v_optimal = v_1
            log_density_optimal = log_density_1
            strategy = "random_perturbation"
        else:
            v_optimal = v_2
            log_density_optimal = log_density_2
            strategy = "cluster_midpoint"
        
        # Prepare for vec2text (768-dim)
        v_optimal_2d = v_optimal.reshape(1, -1).astype(np.float32)
        v_optimal_tensor = torch.tensor(v_optimal_2d, device='mps')
        
        print(f"Inverting embedding shape: {v_optimal_tensor.shape}")
        
        # Invert to text
        generated_texts = vec2text.invert_embeddings(
            embeddings=v_optimal_tensor,
            corrector=corrector
        )
        
        generated_text = generated_texts[0] if isinstance(generated_texts, list) else generated_texts
        
        print(f"\nGenerated Research Gap Idea:\n{generated_text}")
        
        # Also analyze existing gaps
        existing_gaps = []
        sorted_gap_indices = gap_indices[np.argsort(log_probs[gap_indices])][:3]
        
        for idx in sorted_gap_indices:
            existing_gaps.append({
                'id': ids[idx],
                'log_density': float(log_probs[idx]),
                'document': documents[idx][:300],
                'metadata': metadatas[idx]
            })
        
        # Use Claude to enhance the generated idea
        enhanced_idea = None
        
        if client:
            try:
                prompt = f"""A novel research concept was generated by finding a low-density region in the embedding space:

                        "{generated_text}"

                        This concept is in an underexplored area (log density: {log_density_optimal:.2f}).

                        Elaborate on this research idea:
                        1. What specific research questions could be explored?
                        2. What methodologies would be appropriate?
                        3. What interdisciplinary connections could be made?

                        Keep it concise (3-4 sentences)."""

                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                enhanced_idea = message.content[0].text
            except Exception as e:
                print(f"Error enhancing idea with Claude: {e}")

        collection.delete(ids=ids)
        return jsonify(
            enhanced_idea = enhanced_idea,
        ), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@bp.get('/get3Dpoints')
def get3Dpoints():
    collection = get_chroma_collection()
    results = collection.get(
        include=['embeddings', 'metadatas'],
    )
    
    emb = results['embeddings']
    
    #convert the embedding to 3D 
    proj_3d = umap_3d.fit_transform(emb)
    #make clusters
    clusterer.fit(proj_3d)

    labels = clusterer.labels_
    labels = labels.tolist()
    embArr = proj_3d.tolist()

    links = [ item['link'] for item in results['metadatas']]
    titles = results['ids']

    return {
        "results" : [{
            'title': title,
            'link' : link,
            'embedding' : embedding,
            'clusterId' : id
        } for title, link, embedding, id in zip(titles, links, embArr, labels) ]
    }

