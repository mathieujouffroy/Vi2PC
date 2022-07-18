import itertools
import threading
import time
import sys
import h5py
from cli_utils import bcolors, strawb, animate
from dataloader import PlantDataset, load_hdf5, store_hdf5, create_hf_ds
from leaf_segmentation import *
import plantcv as pcv
import json
from sklearn.model_selection import train_test_split

def get_split_sets(seed, class_type, images, labels):
    """
    Prepare the inputs and target split sets for a given classification.

    Args:
        args(ArgumentParser): Object that holds multiple training parameters
        images(numpy.array): images array
        labels(numpy.array): label array
        logger():
    Returns:
        X_splits(list): list containing the images split sets
        y_splits(list): list containing the labels split sets
    """

    # Split train, valid, test
    X_train, X_tmp, y_train, y_tmp = train_test_split(
        images, labels, test_size=0.30, stratify=labels, random_state=seed)
    X_valid, X_test, y_valid, y_test = train_test_split(
        X_tmp, y_tmp, test_size=0.50, stratify=y_tmp, random_state=seed)
    label_split_lst = list([y_train, y_valid, y_test])
    name_lst = list(['Train', 'Valid', 'Test'])

    # Display counts for unique values in each set
    for value, d_set in zip(label_split_lst, name_lst):
        (unique, cnt) = np.unique(value, return_counts=True)
        print(f"  {d_set} Labels:")
        for name, counts in zip(unique, cnt):
            print(f"    {name} = {counts}")
        if class_type == 'healthy':
            print(f"  Ratio Healthy = {cnt[0]/(cnt[0]+cnt[1])}")
            print(f"  Ratio Sick = {cnt[1]/(cnt[0]+cnt[1])}\n")

    if class_type == 'healthy':
        y_train = y_train[:, np.newaxis]
        y_valid = y_valid[:, np.newaxis]
        y_test = y_test[:, np.newaxis]

    return [X_train, X_valid, X_test], label_split_lst


def main():
    if len(sys.argv) == 2:
        quit_lst = ['q', 'quit']
        yes = ['y', 'yes']
        no = ['n', 'no']
        plant_data = PlantDataset(sys.argv[1], verbose=True)
        plant_df = plant_data.load_data()
        print("load data done")
        print(
            f"\n\n{bcolors.OKGREEN}==================  POP FARM : Plant Phenotyping  =================={bcolors.ENDC}")
        print(f"{bcolors.FAIL}{strawb}{bcolors.ENDC}\n\n")
        try:
            while not False:
                print(
                    f"{bcolors.UNDERLINE}type q or quit to exit the program{bcolors.ENDC}\n")

                label_type = input(f'Enter the label type: plant, disease, healthy, gen_disease\n').lower()
                assert label_type in ['plant', 'disease', 'healthy', 'gen_disease']
                images, labels = plant_data.get_relevant_images_labels(label_type)
                print("load relevant data done")
                noseg_images = []
                for img in images:
                    noseg_images.append(cv2.resize(img, dsize=(224, 224), interpolation=cv2.INTER_AREA))
                noseg_images = np.array(noseg_images)
                X_splits, y_splits = get_split_sets(42, label_type, noseg_images, labels)
                X_train, X_valid, X_test = X_splits
                y_train, y_valid, y_test = y_splits

                # Get stats from training set for data preprocessing
                X_train_mean_rgb = np.mean(X_train, axis=tuple(range(X_train.ndim-1)))
                X_train_std_rgb = np.std(X_train, axis=tuple(range(X_train.ndim-1)))
                train_stats = {
                    'X_train_mean_rgb': X_train_mean_rgb.tolist(),
                    'X_train_std_rgb': X_train_std_rgb.tolist()
                }
                print(f"X train mean : {X_train_mean_rgb}")
                print(f"X train std : {X_train_std_rgb}")
                with open(f"{label_type}_train_stats_224.json", "w") as outfile:
                    json.dump(train_stats, outfile, indent=4)

                ###
                # CREATE TRANSFORMER DATASET
                if label_type !=  'healthy':
                    if label_type == 'disease':
                        label_map_path = '../resources/diseases_label_map.json'
                    elif label_type == 'plants':
                        label_map_path = '../resources/plants_label_map.json'
                    else:
                        label_map_path = '../resources/general_diseases_label_map.json'
                    with open(label_map_path) as f:
                        id2label = json.load(f)
                    class_names = [str(v) for k,v in id2label.items()]
                else:
                    class_names = ['healthy', 'not_healthy']
                print(f"  Class names = {class_names}")

                train_sets = create_hf_ds(X_train, y_train, class_names)
                train_sets.save_to_disk("../resources/transformers_ds/train")
                valid_sets = create_hf_ds(X_valid, y_valid, class_names)
                valid_sets.save_to_disk("../resources/transformers_ds/valid")
                test_sets = create_hf_ds(X_test, y_test, class_names)
                test_sets.save_to_disk("../resources/transformers_ds/test")
                ###

                #store_hdf5(f"{label_type}_{plant_data.img_nbr}_ds_224.h5", X_train, X_valid, X_test, y_train, y_valid, y_test)

                options = input(f"""{bcolors.OKBLUE}[0]{bcolors.ENDC} -- Visualization of your farm\n{bcolors.OKBLUE}[1]{bcolors.ENDC} -- Generate Segmented Leaves HSV Mask\n{bcolors.OKBLUE}[2]{bcolors.ENDC} -- Generate Segmented Leaves HSV Mask + dist transform\n{bcolors.OKBLUE}[3]{bcolors.ENDC} -- Extract Features for ML Classification\n{bcolors.OKBLUE}[4]{bcolors.ENDC} -- Preprocess for CNN\n{bcolors.OKBLUE}[5]{bcolors.ENDC} -- Plant Health Classification{bcolors.OKBLUE}\n[6]{bcolors.ENDC} -- Plant Classification{bcolors.OKBLUE}\n[7]{bcolors.ENDC} -- Plant Disease Classification\n{bcolors.OKBLUE}[q]{bcolors.ENDC} -- Quit\n""")

                if options == '0':
                    print('Dataset Distribution')
                    plant_data.dataset_distribution(plant_df)
                    plant_data.plant_overview(plant_df)
                    print('Done')

                if options == '1':
                    print('Leag Segmentation HSV mask')
                    p_option = input(
                        f"""Chose Image adjustments (brightness, contrast):\n{bcolors.OKBLUE}[0]{bcolors.ENDC} -- No Adjustments\n{bcolors.OKBLUE}[1]{bcolors.ENDC} -- Adjust Lightness\n{bcolors.OKBLUE}[2]{bcolors.ENDC} -- Adjust Contrast\n{bcolors.OKBLUE}[3]{bcolors.ENDC} -- Adjust Lightness and Contrast\n""")
                    if p_option in ['0', '1', '2', '3']:
                        seg_imgs = []
                        for img in images:
                            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                            img_noback = remove_background(
                                rgb_img, p_type=int(p_option))  # , verbose=True)
                            seg_imgs.append(img_noback)
                        seg_imgs = np.array(seg_imgs)
                        images = seg_imgs
                        print('Done')

                    else:
                        print('Invalid option')
                        continue
                    print('Done')

                if options == '2':
                    print('Leag Segmentation HSV mask + dist transform')
                    p_option = input(
                        f"""Chose Image adjustments (brightness, contrast):\n{bcolors.OKBLUE}[0]{bcolors.ENDC} -- No Adjustments\n{bcolors.OKBLUE}[1]{bcolors.ENDC} -- Adjust Lightness\n{bcolors.OKBLUE}[2]{bcolors.ENDC} -- Adjust Contrast\n{bcolors.OKBLUE}[3]{bcolors.ENDC} -- Adjust Lightness and Contrast\n""")
                    if p_option in ['0', '1', '2', '3']:
                        seg_imgs = []
                        for img in images:
                            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                            img_noback = remove_background(
                                rgb_img, p_type=int(p_option), dist=True)
                            seg_imgs.append(img_noback)
                        seg_imgs = np.array(seg_imgs)
                        images = seg_imgs
                    else:
                        print('Invalid option')
                        continue
                    print('Done')

                if options in ['1', '2']:
                    dataset_name = f"segm_{label_type}_{plant_data.img_nbr}_ds_224.h5"
                    seg_imgs = []
                    for img in images:
                        seg_imgs.append(cv2.resize(img, dsize=(224, 224), interpolation=cv2.INTER_AREA))
                    seg_imgs = np.array(seg_imgs)
                    X_splits, y_splits = get_split_sets(42, label_type, images, labels)
                    X_train, X_valid, X_test = X_splits
                    y_train, y_valid, y_test = y_splits
                    # Get stats from training set for data preprocessing
                    X_train_mean_rgb = np.mean(X_train, axis=tuple(range(X_train.ndim-1)))
                    X_train_std_rgb = np.std(X_train, axis=tuple(range(X_train.ndim-1)))
                    train_stats = {
                        'X_train_mean_rgb': X_train_mean_rgb.tolist(),
                        'X_train_std_rgb': X_train_std_rgb.tolist()
                    }
                    print(f"X train mean : {X_train_mean_rgb}")
                    print(f"X train std : {X_train_std_rgb}")
                    with open(f"seg_{label_type}_train_stats_224.json", "w") as outfile:
                        json.dump(train_stats, outfile, indent=4)
                    store_hdf5(dataset_name,  X_train, X_valid, X_test, y_train, y_valid, y_test)

                if options == '3':
                    print('test 3')
                if options.lower() in quit_lst:
                    print("Bye !")
                    break
        except EOFError:  # for ctrl + c
          print("\nBye !")
          quit = True
        except KeyboardInterrupt:  # for ctrl + d
          print("\nSee you soon !")
          quit = True
    else:
        print(
            f"{bcolors.FAIL}Input the directory of your images to run the program{bcolors.ENDC}")
        print(
            f"{bcolors.WARNING}usage:\t{bcolors.ENDC}python cli.py <images_directory>")
        return


if __name__ == "__main__":
    main()
