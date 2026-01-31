import pandas as pd
from django.db.models import F
from django.utils import timezone
from datetime import timedelta
from analytics.models import SalesLine

class ReorderPredictor:
    """
    Local AI Service for predicting reorder needs based on purchase cycles.
    Optimized for performance: uses vectorized Pandas operations.
    """
    
    def __init__(self, pharmacy_id, LOOKBACK_DAYS=180, MIN_ORDERS=2):
        self.pharmacy_id = pharmacy_id
        self.lookback_days = LOOKBACK_DAYS
        self.min_orders = MIN_ORDERS

    def get_suggestions(self):
        """
        Returns a list of products that are 'due' for reordering.
        Structure: [{'product_name': str, 'days_since_last': int, 'avg_cycle': int, 'confidence': str}]
        """
        start_date = timezone.now().date() - timedelta(days=self.lookback_days)
        
        # 1. Efficient DB Query: Fetch only necessary fields
        # Filter by date range first to minimize memory usage
        lines = SalesLine.objects.filter(
            document__pharmacy_id=self.pharmacy_id,
            document__date__date__gte=start_date,
            document__status='COMPLETED' # Only consider actual consumption
        ).values(
            prod_name=F('product__name'),
            date=F('document__date__date')
        ).order_by('product__id', 'document__date')

        if not lines:
            return []

        # 2. Convert to Pandas DataFrame
        df = pd.DataFrame(lines)
        
        if df.empty:
            return []

        # 3. Pre-process
        df['date'] = pd.to_datetime(df['date'])
        
        # 4. Group by Product and Calculate Cycles
        # We need products with at least N orders to establish a cycle
        order_counts = df.groupby('prod_name')['date'].nunique()
        recurring_products = order_counts[order_counts >= self.min_orders].index
        
        if len(recurring_products) == 0:
            return []
            
        df_filtered = df[df['prod_name'].isin(recurring_products)]
        
        # 5. Core Logic: Gap Analysis
        suggestions = []
        today = pd.Timestamp.now().normalize()
        
        for product_name, group in df_filtered.groupby('prod_name'):
            # clean duplicates on same day if any (multiple orders same day count as 1 event)
            dates = group['date'].drop_duplicates().sort_values()
            
            # Calculate gaps (diff between dates)
            gaps = dates.diff().dt.days.dropna()
            
            if len(gaps) == 0:
                continue
                
            avg_cycle = gaps.mean()
            last_order_date = dates.iloc[-1]
            days_since_last = (today - last_order_date).days

            # 6. Detection Threshold
            # If time passed > average cycle + buffer (e.g. 20%), it's due.
            # But not TOO long ago (e.g. 3x cycle), which implies they stopped buying it.
            
            buffer = 0.2
            threshold = avg_cycle * (1 + buffer)
            abandoned_threshold = avg_cycle * 4 

            if days_since_last > threshold and days_since_last < abandoned_threshold:
                suggestions.append({
                    'product_name': product_name,
                    'days_since_last': int(days_since_last),
                    'avg_cycle': int(round(avg_cycle)),
                    'reason': f"Solía pedir cada {int(round(avg_cycle))} días"
                })
        
        # Sort by most urgent (highest ratio of days_since / avg_cycle)
        suggestions.sort(key=lambda x: x['days_since_last'] / x['avg_cycle'], reverse=True)
        
        return suggestions[:5] # Top 5 only
