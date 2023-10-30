from kmeans import KMeans
import pandas as pd
from sklearn.model_selection import train_test_split
import csv
import sys
import numpy as np
from preprocessor import Preprocessor
import os
import pickle
import matplotlib.pyplot as plt
from metricas import Metrics
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans as KMeans_sklearn
from collections import Counter

#Opciones:
#dar un diccionario de numeros y labels "oficial para cambiarlos"
#gudardar fichero preprocesado o usar uno existente

#--------------------------------------------------------#
# Varibales para configurar el comportamiento del script #
#--------------------------------------------------------#
# Preproceso
# ----------
soloPreproceso = False
preprocessed_file = "50000instancias_prep.csv"
# If preprocessed_file == None
unpreprocessed_file = "test50000.csv"
guardarPreproceso = "test50000_prep.csv"
pca_dimensions = 200
# If preprocessed_file not None
# Se usa la variable preprocessed_file
# If soloPreproceso == True
# No se ejecuta nada mas de las variables de abajo

train = True # True: train, False: predict
# Entrenamiento (If train == True)
# --------------------------------
n_clusters = 3
maxIter = None
tolerance = 1e-4 # If maxIter == None, stop when has converged using this tolerance
centorids_init = "space_division_init" #random_init, space_division_init, separated_init
p_minkowski = 2
test_size = 0.2 #20%
saveModeloKmeans = "50000instancias_kmeans_model.pkl" #None if you do not want to save model to predict later
imprimirMetricas = True
# If imprimirMetricas == True
n_codos = None # None if not want to make elbow method
numIteracionesCodos = None

# Predicciones (If train == False)
# --------------------------------
useModeloKmeans = "kmeans_model.pkl"
doc2vec_model = "100lineas_doc2vec.model" # None to train, else use trained model to predict
pca_model = "100lineas_pca.model"
output_prediction_file = "predicted.csv"

"""
# Fichero que representa las asignaciones oficiales tras ver las asignaciones numericas
assignLabels = None # {0: "depresion", 1: "" 2: "", etc...}
"""

def saveAssignedPredictions(filename, assigned_labels):
    with open(filename, "w") as file:
        writter = csv.writer(file)
        for post,label in assigned_labels.items():
            if post in vectors_list:
                idx = vectors_list.index(post)
                """if assignLabels:
                    writter.writerow([x[idx], assignLabels[label]])
                else:
                    writter.writerow([x[idx], label])"""
                writter.writerow([x[idx], label])

def metodo_codo(dataset, num_codos, numIteracionesCodos):
    lista100clusters = []
    if numIteracionesCodos and num_codos:
        for i in range(numIteracionesCodos):
            sum_of_squared_distances = []
            print(f"iter {i}")
            for k in range(1, num_codos+1):
                print(f"codo {k}")
                kmeans = KMeans(k, maxIter, centorids_init, p_minkowski, tolerance)
                kmeans.fit(dataset)
                sum_of_squared_distances.append(kmeans.inertia)
            """
            #------------------------------------------------
            wcss = sum_of_squared_distances
            for i in range(1, len(wcss) - 1):
                slope_current = wcss[i] - wcss[i - 1]
                slope_next = wcss[i + 1] - wcss[i]
    
                # Verificar si la pendiente cambia significativamente
                if slope_next < 0.5 * slope_current:
                   optimal_clusters = i + 1  # Agregamos 1 porque el índice comienza en 1
                    break
            k = optimal_clusters
            #------------------------------------------------
            # Calcular las derivadas de segundo orden (cambios en la pendiente)
            second_derivative = np.gradient(np.gradient(wcss))
            # Encontrar el índice del máximo cambio en la pendiente
            optimal_clusters = np.argmax(second_derivative) + 1
            k = optimal_clusters
            #------------------------------------------------
            plt.scatter(optimal_clusters, wcss[optimal_clusters - 1], c='red', label='Punto óptimo')
            plt.legend()
            plt.show()
            """
            k = sum_of_squared_distances.index(min(sum_of_squared_distances))+1
            plt.figure(figsize=(8, 6))
            plt.plot(range(1, num_codos+1), sum_of_squared_distances, marker='o', linestyle='-', color='b')
            plt.xlabel('Número de clusters (k)')
            plt.ylabel('Suma de distancias al cuadrado')
            plt.title('Método del codo para seleccionar k')
            plt.grid(True)
            plt.savefig(f'metodo_{num_codos}_codos_{k}_clusters.png', format='png')
            plt.close()
            lista100clusters.append(k)
        frecuencias = Counter(lista100clusters)
        frecuencias = dict(frecuencias)
        print(frecuencias)
        k = max(frecuencias, key=frecuencias.get)
        print(k)
        plt.bar(frecuencias.keys(),frecuencias.values())
        # Agregar etiquetas de valor en las barras
        for index, value in frecuencias.items():
            plt.text(index, value, str(value), ha='center', va='bottom')
        plt.xlabel('Número de Clusters')
        plt.ylabel('Frecuencia de pruebas')
        plt.title(f'Numero de clusters en {numIteracionesCodos} iteracinones')
        plt.savefig(f'{numIteracionesCodos}_elbow_counts_per_cluster.png', format='png')
        plt.close()
        print(f"Saved_image: {numIteracionesCodos}_elbow_counts_per_cluster.png")
    else:
        if num_codos:
            sum_of_squared_distances = []
            for k in range(1, num_codos+1):
                kmeans = KMeans(k, maxIter, centorids_init, p_minkowski, tolerance)
                kmeans.fit(dataset)
                sum_of_squared_distances.append(kmeans.inertia)
            k = sum_of_squared_distances.index(min(sum_of_squared_distances))+1
            plt.figure(figsize=(8, 6))
            plt.plot(range(1, num_codos+1), sum_of_squared_distances, marker='o', linestyle='-', color='b')
            plt.xlabel('Número de clusters (k)')
            plt.ylabel('Suma de distancias al cuadrado')
            plt.title('Método del codo para seleccionar k')
            plt.grid(True)
            plt.savefig(f'metodo_{num_codos}_codos_{k}_clusters.png', format='png')
            plt.close()
    #for idx,inertia in enumerate(sum_of_squared_distances):
    #    print(f"{idx+1} clusters: {inertia}")
    return k

def load_dataset(filename):
    dataset = pd.read_csv(filename)
    return np.asarray(dataset["text"]),np.asarray(dataset["class"])

def plot_clusters_2d(clusters, centroids, filename):
    # Lista que contiene todos los puntos (los centroides no)
    points = [point for cluster in clusters for point in cluster]

    # Reducir dimensionalidad a 2D usando PCA
    pca = PCA(n_components=2)
    reduced_points = pca.fit_transform(points)
    reduced_centroids = pca.transform(centroids)
    predicted_labels = [label for label in kmeans.assign_numeric_labels(clusters).values()]

    samples = len(points)
    #sc = plt.scatter(X_train_PCAspace[:samples,0],X_train_PCAspace[:samples,1], cmap=plt.cm.get_cmap('nipy_spectral', 10),c=kmeansLabels[:samples])
    # Imprimir los puntos
    plt.scatter(reduced_points[:samples, 0], reduced_points[:samples, 1], c=predicted_labels[:samples], cmap='viridis', marker='o', label='Points')

    # Imprimir los centroides
    plt.scatter(reduced_centroids[:samples, 0], reduced_centroids[:samples, 1], c='red', marker='X', s=200, label='Centroids')

    #for i in range(samples):
    #    plt.text(points[i][0],points[i][1], predicted_labels[i])

    # Poner etiquetas
    plt.xlabel('Principal Component 1')
    plt.ylabel('Principal Component 2')
    plt.title('2D PCA of Clusters and Centroids')
    plt.legend()
    
    # Guardar la imagen
    plt.savefig(f'{filename}', format='png')
    plt.close()

if __name__ == "__main__":
    x = None
    y = None
    vectors_list = None
    if preprocessed_file == None:
        print("Preproceso")
        print("----------")
        # Cargar el fichero de datos
        x,y = load_dataset(unpreprocessed_file)
        preprocessor = Preprocessor()
        if doc2vec_model and pca_model and not train:
            x_prep,y_prep,doc2vec_model,pca_model = preprocessor.doc2vec(x, y, pca_dimensions=pca_dimensions, doc2vec_model=doc2vec_model, pca_model=pca_model)
        else:
            x_prep,y_prep,doc2vec_model,pca_model = preprocessor.doc2vec(x, y, pca_dimensions=pca_dimensions, doc2vec_model=None, pca_model=None)
        vectors_list = x_prep.tolist()
        vectors_list = [tuple(point) for point in vectors_list]
        labels_list = y_prep
        print(f"[*] Preproceso listo")
        if guardarPreproceso != None:
            with open(guardarPreproceso, "w") as file:
                writer = csv.writer(file)
                writer.writerow(["text","class"])
                for idx,point in enumerate(vectors_list):
                    writer.writerow([point,y[idx]])
            print(f"    Fichero guardado: {guardarPreproceso}")
            if train:
                doc2vec_model.save(unpreprocessed_file.split(".")[0]+"_doc2vec.model")
                with open(unpreprocessed_file.split(".")[0]+"_pca.model", "wb") as file:
                    pickle.dump(pca_model, file)
                print(f"    Fichero guardado: {unpreprocessed_file.split('.')[0]+'_doc2vec.model'}")
                print(f"    Fichero guardado: {unpreprocessed_file.split('.')[0]+'_pca.model'}")
            print()
        if soloPreproceso:
            sys.exit(0)
    else:
        if not os.path.exists(preprocessed_file):
            print(f"Error: {preprocessed_file} not found")
            sys.exit(1)
        x_prep,y_prep = load_dataset(preprocessed_file)
        vectors_list = [eval(point) for point in x_prep]
        labels_list = y_prep
    
    if train: # Do train
        # Separar los datos en 2 conjuntos, train y test
        x_train,x_test,y_train,y_test = train_test_split(vectors_list, labels_list, test_size=test_size)
        kmeans = KMeans(n_clusters, maxIter, centorids_init, p_minkowski, tolerance)
        print("Entrenamiento")
        print("-------------")
        print("[*] Entrenando kmeans...")
        print()
        centroids, clusters = kmeans.fit(x_train)

        y_test_predicted = kmeans.predict(x_test)

        # Elegir el numero de clusters optimo con el metodo de los codos
        if imprimirMetricas:
            metricas = Metrics()

            print("Metricas")
            print("--------")
            if n_codos:
                n_clusters_optimo = metodo_codo(vectors_list, n_codos, numIteracionesCodos)
                kmeans_codos = KMeans(n_clusters_optimo, maxIter, centorids_init, p_minkowski, tolerance)
                centroids_codos, clusters_codos = kmeans_codos.fit(x_train)
                print(f"[*] Numero optimo de clusters (elbow method): {n_clusters_optimo}")
                print(f"    Imagen guardada: metodo_{n_codos}_codos.png")
            print(f"[*] SSE (Sum of Squared Errors): {kmeans.inertia}")
            print(f"[*] PCA en de los clusters en 2D:")
            plot_clusters_2d(clusters, centroids, "2_dimensions_pca.png")
            print(f"    Imagen guardada: 2_dimensions_pca.png")
            if n_codos:
                print(f"[*] PCA en de los clusters en 2D segun el numero de clusters optimo (elbow method):")
                plot_clusters_2d(clusters_codos, centroids_codos, f"2_dimensions_pca_elbow_{n_clusters_optimo}_clusters.png")
                print(f"    Imagen guardada: 2_dimensions_pca_elbow_{n_clusters_optimo}_clusters.png")
            # Comparativa KMeans implementado y sklearn con el mismo numero de clusters
            print(f"[*] Nuestras metricas")
            metricas.calculate_all_metrics(y_test, np.array(list(y_test_predicted.values())), x_test)
            kmeans_sklearn = KMeans_sklearn(n_clusters=n_clusters)
            kmeans_sklearn.fit(x_train)
            y_test_predicted = kmeans_sklearn.predict(x_test)
            print(f"[*] sklearn metricas")
            print(y_test_predicted)
            metricas.calculate_all_metrics(y_test, y_test_predicted, x_test)
            print()
    
        assigned_labels = kmeans.assign_numeric_labels(clusters)
        #saveAssignedPredictions("train_labels_assigned.csv", assigned_labels)
        if saveModeloKmeans:
            with open(saveModeloKmeans, "wb") as file:
                pickle.dump(kmeans, file)
    else: # Do predict
        if useModeloKmeans:
            with open(useModeloKmeans, "rb") as file:
                kmeans = pickle.load(file)
        else:
            #kmeans = KMeans(vectors_list, n_clusters, maxIter, centorids_init, p_minkowski, tolerance)
            #centroids, clusters = kmeans.fit()
            raise Exception('Usa un modelo de kmeans')
        print("Predicciones")
        print("------------")
        assigned_labels = kmeans.predict(vectors_list)
        #print(assigned_labels)
        #saveAssignedPredictions("test_labels_assigned.csv", assigned_labels)
    
        if output_prediction_file:
            with open(output_prediction_file, "w") as file:
                writter = csv.writer(file)
                for post,label in assigned_labels.items():
                    if post in vectors_list:
                        idx = vectors_list.index(post)
                        """if assignLabels:
                            writter.writerow([x[idx], assignLabels[label]])
                        else:
                            writter.writerow([x[idx], label])"""
                        writter.writerow([x[idx], label])
            print(f"[*] Fichero guardado: {output_prediction_file}")



"""
# mapping
labels_frecuency = {label: [0,0,0] for label in set(y)}
for post,label in assigned_labels.items():
    if post in vectors_list:
        idx = vectors_list.index(post)
        original_label = y[idx]
        labels_frecuency[original_label][label] += 1
        #print(original_label)
        #print(label)
print(labels_frecuency)
new_assigned_labels = {}
for post,label in assigned_labels.items():
    for original_label in labels_frecuency:
        idx = labels_frecuency[original_label].index(max(labels_frecuency[original_label]))
        if label == idx:
            new_assigned_labels[label] = original_label
print(new_assigned_labels)
"""
