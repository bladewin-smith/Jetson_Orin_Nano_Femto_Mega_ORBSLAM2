#!/usr/bin/env bash
set -e

echo "Configuring and building Thirdparty/DBoW2 ..."

cd Thirdparty/DBoW2
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j

cd ../../g2o

echo "Configuring and building Thirdparty/g2o ..."

mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j

cd ../../../

echo "Uncompress vocabulary ..."

cd Vocabulary
if [ -f ORBvoc.txt.tar.gz ]; then
  tar -xf ORBvoc.txt.tar.gz
elif [ -f ORBvoc.bin ]; then
  echo "ORBvoc.txt.tar.gz not found, using existing ORBvoc.bin."
else
  echo "Warning: ORBvoc.txt.tar.gz and ORBvoc.bin were not found."
fi
cd ..

echo "Configuring and building ORB_SLAM2 ..."

mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j

cd ..

echo "Converting vocabulary to binary"
if [ -f Vocabulary/ORBvoc.txt ]; then
  chmod +x ./tools/bin_vocabulary
  ./tools/bin_vocabulary
elif [ -f Vocabulary/ORBvoc.bin ]; then
  echo "Vocabulary/ORBvoc.bin already exists, skip conversion."
else
  echo "Skip vocabulary conversion because Vocabulary/ORBvoc.txt is missing."
fi
