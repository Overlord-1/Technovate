from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view
import pandas as pd
import numpy as np
import joblib
from bson import ObjectId
from bson.errors import InvalidId
import json
import traceback
from datetime import datetime

# Load CSV data
def load_csv_data(csv_path='C:/Users/vinay/Desktop/technovate/Technovate/Carbon Emission.csv'):
    """Load and return the CSV data"""
    return pd.read_csv(csv_path)

def convert_to_python_types(obj):
    """Convert NumPy types to Python native types"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_python_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_python_types(item) for item in obj]
    return obj


def load_model(model_path='C:/Users/vinay/Desktop/technovate/Technovate/temp/carbon_footprint_model.pkl'):
    """Load the trained model"""
    import os
    # Normalize the path separators
    model_path = os.path.normpath(model_path)
    return joblib.load(model_path)

def preprocess_data(data):
    """Preprocess single user data for model prediction"""
    from sklearn.preprocessing import LabelEncoder
    
    categorical_cols = ['bodyType', 'sex', 'diet', 'howOftenShower', 'heatingEnergySource',
                       'transport', 'vehicleType', 'socialActivity', 'frequencyOfTravelingByAir',
                       'wasteBagSize', 'energyEfficiency']
    
    processed_data = {}
    le = LabelEncoder()
    
    # Process categorical columns
    for col in categorical_cols:
        if col in data:
            if isinstance(data[col], bool):
                processed_data[col] = int(data[col])
            else:
                processed_data[col] = le.fit_transform([str(data[col])])[0]
    
    # Process numerical columns
    numerical_cols = ['monthlyGroceryBill', 'vehicleMonthlyDistanceKm', 'wasteBagWeeklyCount',
                     'howLongTvpCDailyHour', 'howManyNewClothesMonthly', 'howLongInternetDailyHour']
    
    for col in numerical_cols:
        if col in data:
            processed_data[col] = float(data[col])
    
    # Process array fields
    if 'recycling' in data:
        processed_data['recycling_count'] = len(data['recycling'])
    if 'cookingWith' in data:
        processed_data['cooking_methods_count'] = len(data['cookingWith'])
    
    # Ensure consistent order of features
    all_features = categorical_cols + numerical_cols + ['recycling_count', 'cooking_methods_count']
    ordered_data = [processed_data.get(feature, 0) for feature in all_features]
    
    return ordered_data

def calculate_percentile_rank(value, population_values):
    """Calculate the percentile rank of a value in a population"""
    if len(population_values) == 0:
        return 50.0
    population_values = np.array(population_values)
    result = np.sum(population_values < value) / len(population_values) * 100
    return float(result)

def calculate_stats(value, population_values):
    """Calculate statistical measures for a value against population"""
    # Convert to numpy array if not already
    population_values = np.array(population_values)
    
    # Check if array is empty using size property
    if population_values.size == 0:
        return {
            'your_value': float(value),
            'population_mean': float(value),
            'difference_from_mean': 0.0,
            'percentile_rank': 50.0,
            'population_standard_deviation': 0.0
        }
    
    # Calculate statistics
    mean = float(np.mean(population_values))
    std = float(np.std(population_values))
    percentile = float(calculate_percentile_rank(value, population_values))
    diff_from_mean = float(value - mean)
    
    return {
        'your_value': float(value),
        'population_mean': mean,
        'difference_from_mean': diff_from_mean,
        'percentile_rank': percentile,
        'population_standard_deviation': std
    }   

def get_emission_category(prediction):
    """Determine emission category based on prediction value"""
    if prediction > 3000:
        return 'Very High'
    elif prediction > 2500:
        return 'High'
    elif prediction > 2000:
        return 'Medium'
    elif prediction > 1500:
        return 'Low'
    return 'Very Low'

def generate_detailed_recommendations(user_data):
    """Generate detailed, personalized recommendations based on user data"""
    recommendations = {
        'immediate_actions': [],
        'medium_term_goals': [],
        'long_term_changes': []
    }
    
    # Grocery-related recommendations
    if user_data.get('monthlyGroceryBill', 0) > 400:
        recommendations['immediate_actions'].append({
            'action': 'Reduce monthly grocery spending',
            'impact_level': 'Medium',
            'suggestion': 'Try to reduce food waste by planning meals in advance and buying in bulk.'
        })

    # Vehicle-related recommendations
    if user_data.get('vehicleMonthlyDistanceKm', 0) > 1500:
        recommendations['immediate_actions'].append({
            'action': 'Limit vehicle usage',
            'impact_level': 'High',
            'suggestion': 'Consider carpooling or using public transportation when possible.'
        })

    # Waste-related recommendations
    if user_data.get('wasteBagWeeklyCount', 0) > 3:
        recommendations['immediate_actions'].append({
            'action': 'Reduce waste production',
            'impact_level': 'Medium',
            'suggestion': 'Implement recycling and composting practices.'
        })

    # Medium-term recommendations
    recommendations['medium_term_goals'].extend([
        {
            'action': 'Energy-efficient appliances',
            'impact_level': 'High',
            'suggestion': 'Upgrade to energy-efficient appliances and install programmable thermostats.'
        },
        {
            'action': 'Adopt plant-based diet',
            'impact_level': 'High',
            'suggestion': 'Gradually increase plant-based meals in your diet.'
        }
    ])

    # Long-term recommendations
    if user_data.get('vehicleType') != 'Electric':
        recommendations['long_term_changes'].append({
            'action': 'Switch to electric vehicle',
            'impact_level': 'Very High',
            'suggestion': 'Consider switching to an electric or hybrid vehicle.'
        })

    if user_data.get('heatingEnergySource') != 'Solar':
        recommendations['long_term_changes'].append({
            'action': 'Renewable energy',
            'impact_level': 'Very High',
            'suggestion': 'Install solar panels or other renewable energy systems.'
        })

    return recommendations

def generate_insights_from_csv(user_data, prediction, csv_data):
    """Generate comprehensive insights using CSV data"""
    
    # Map user data keys to CSV columns
    column_mapping = {
        'monthlyGroceryBill': 'Monthly Grocery Bill',
        'vehicleMonthlyDistanceKm': 'Vehicle Monthly Distance Km',
        'wasteBagWeeklyCount': 'Waste Bag Weekly Count',
        'howLongTvpCDailyHour': 'How Long TV PC Daily Hour',
        'howManyNewClothesMonthly': 'How Many New Clothes Monthly'
    }
    
    # Calculate overall statistics using carbon emissions from CSV
    carbon_emissions = csv_data['CarbonEmission'].dropna().values
    mean_emission = np.mean(carbon_emissions)
    std_emission = np.std(carbon_emissions)
    percentile_rank = calculate_percentile_rank(prediction, carbon_emissions)
    diff_from_mean_percent = ((prediction - mean_emission) / mean_emission) * 100 if mean_emission != 0 else 0
    std_from_mean = (prediction - mean_emission) / std_emission if std_emission != 0 else 0
    
    # Calculate comparative stats for each factor
    comparative_stats = {}
    for user_key, csv_col in column_mapping.items():
        population_values = csv_data[csv_col].dropna().values
        user_value = user_data.get(user_key, 0)
        comparative_stats[user_key.lower()] = calculate_stats(user_value, population_values)
    
    return {
        '1. OVERALL SUMMARY': {
            'predicted_emission': float(prediction),
            'percentile_rank': float(percentile_rank),
            'comparison_to_mean': float(diff_from_mean_percent),
            'standard_deviations_from_mean': float(std_from_mean),
            'category': get_emission_category(prediction),
            'population_statistics': {
                'mean': float(mean_emission),
                'std_dev': float(std_emission),
                'sample_size': len(carbon_emissions)
            }
        },
        '2. COMPARATIVE STATS FOR SPECIFIC FACTORS': comparative_stats,
        '3. RECOMMENDATIONS': generate_detailed_recommendations(user_data)
    }

@api_view(['POST'])
def analyze_carbon_footprint(request):
    """Main API endpoint for carbon footprint analysis"""
    try:
        # Load CSV data
        csv_data = load_csv_data()
        
        # Parse request data
        data = json.loads(request.body) if isinstance(request.body, bytes) else request.data
        print("Received data:", data)
        
        # Handle userID
        user_id_str = data.get('userID') or data.get('_id')
        if not user_id_str:
            return JsonResponse({'error': 'userID is required'}, status=400)
        
        try:
            object_id = ObjectId(user_id_str)
        except InvalidId:
            return JsonResponse({
                'error': 'Invalid ID format',
                'received_id': user_id_str,
                'expected_format': '24-character hex string'
            }, status=400)
        
        # Process data and make prediction
        processed_data = preprocess_data(data)
        model = load_model()
        prediction = float(model.predict([processed_data])[0])
        
        # Generate insights and recommendations
        insights = generate_insights_from_csv(data, prediction, csv_data)
        recommendations = generate_detailed_recommendations(data)
        
        # Prepare response
        response_data = {
            'success': True,
            'userId': str(object_id),
            'prediction': prediction,
            'timestamp': datetime.now().isoformat(),
            'insights': insights,
            'recommendations': recommendations,
            'statistics': {
                'percentileRank': float(insights['1. OVERALL SUMMARY']['percentile_rank']),
                'comparisonToMean': float(insights['1. OVERALL SUMMARY']['comparison_to_mean']),
                'standardDeviationsFromMean': float(insights['1. OVERALL SUMMARY']['standard_deviations_from_mean']),
                'emissionCategory': insights['1. OVERALL SUMMARY']['category'],
                'populationStats': insights['1. OVERALL SUMMARY']['population_statistics']
            },
            'comparisons': {
                'grocery': insights['2. COMPARATIVE STATS FOR SPECIFIC FACTORS']['monthlygrocerybill'],
                'vehicleDistance': insights['2. COMPARATIVE STATS FOR SPECIFIC FACTORS']['vehiclemonthlydistancekm'],
                'wasteBags': insights['2. COMPARATIVE STATS FOR SPECIFIC FACTORS']['wastebagweeklycount'],
                'screenTime': insights['2. COMPARATIVE STATS FOR SPECIFIC FACTORS']['howlongtvpcdailyhour'],
                'clothingPurchases': insights['2. COMPARATIVE STATS FOR SPECIFIC FACTORS']['howmanynewclothesmonthly']
            },
            'metadata': {
                'modelVersion': '1.0',
                'lastUpdated': datetime.now().isoformat(),
                'dataVersion': '1.0',
                'dataSource': 'CSV',
                'sampleSize': len(csv_data)
            }
        }
        
        # Convert all numpy types to Python native types
        return JsonResponse(convert_to_python_types(response_data))
        
    except Exception as e:
        print("Error:", str(e))
        print("Traceback:", traceback.format_exc())
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)