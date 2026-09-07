from fastapi import APIRouter, HTTPException, Depends
import networkx as nx
from ...database.connection import db_session
from ...utils.security import get_current_user

router = APIRouter(prefix='/api/graph', tags=['Graph Explorer'])

@router.get('/{txid}')
def get_transaction_graph(txid: str, depth: int = 1, user: dict = Depends(get_current_user)):
    with db_session() as conn:
        target_tx = conn.execute('SELECT * FROM transactions WHERE txid = ?', (txid,)).fetchone()
        if not target_tx:
            raise HTTPException(status_code=404, detail='Transaction not found')
            
        nodes = []
        edges = []
        visited_nodes = set()
        
        # Add primary transaction node
        nodes.append({
            'data': {
                'id': txid,
                'label': f'TX: {txid[:8]}...',
                'type': 'transaction',
                'risk_score': target_tx['risk_score'],
                'risk_level': target_tx['risk_level'],
                'total_sats': target_tx['total_output_sats'],
                'is_target': True
            }
        })
        visited_nodes.add(txid)
        
        # Upstream Inputs
        inputs = conn.execute('SELECT * FROM transaction_inputs WHERE txid = ?', (txid,)).fetchall()
        for inp in inputs:
            addr = inp['address'] or f"PrevTx:{str(inp['prev_txid'])[:8]}"
            addr_id = f"addr_{addr}"
            if addr_id not in visited_nodes:
                nodes.append({
                    'data': {
                        'id': addr_id,
                        'label': f'{addr[:10]}...',
                        'type': 'address',
                        'address': addr,
                        'value_sats': inp['value_sats'],
                        'is_input': True
                    }
                })
                visited_nodes.add(addr_id)
            edges.append({
                'data': {
                    'id': f'{addr_id}->{txid}',
                    'source': addr_id,
                    'target': txid,
                    'label': f"{inp['value_sats']:,} sats"
                }
            })
            
        # Downstream Outputs
        outputs = conn.execute('SELECT * FROM transaction_outputs WHERE txid = ?', (txid,)).fetchall()
        for out in outputs:
            addr = out['address'] or f"OutVout:{out['output_index']}"
            addr_id = f"addr_{addr}"
            if addr_id not in visited_nodes:
                nodes.append({
                    'data': {
                        'id': addr_id,
                        'label': f'{addr[:10]}...',
                        'type': 'address',
                        'address': addr,
                        'value_sats': out['value_sats'],
                        'is_output': True
                    }
                })
                visited_nodes.add(addr_id)
            edges.append({
                'data': {
                    'id': f'{txid}->{addr_id}',
                    'source': txid,
                    'target': addr_id,
                    'label': f"{out['value_sats']:,} sats"
                }
            })
            
        return {
            'target_txid': txid,
            'node_count': len(nodes),
            'edge_count': len(edges),
            'elements': {'nodes': nodes, 'edges': edges},
            'disclaimer': 'Graph relationships display UTXO provenance. Graph adjacency does NOT prove criminal conspiracy or common real-world ownership.'
        }
